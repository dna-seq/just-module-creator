# Dogfooding — open findings

Open quirks, bugs and UX gaps found by **using the shipped surface for real
work**, not by testing it. Read before touching the tool surface.

Findings carry stable `F#` IDs and **move** between files rather than being
duplicated: resolved here → [previous_issues.md](previous_issues.md); blocked on
an upstream change → [just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).
One legitimately appears in two files when we have mitigated it and upstream
still owes the fix.

Layer 1 (the suite) proves the code does what it was told. This asks whether it
is usable, and what is missing.

---

## F128 — a session in this checkout runs this checkout's server with the released 0.47.0's skills

**Found:** 2026-11-07, loading `create-module` for the HTT probe · **Severity:** medium (low today, see the
diff) · **Status:** open; the user-scope setting is the person's, asked on the desk as #229 (default: leave it,
and the tester reads the checkout's `skills/` by hand)

CLAUDE.md §11: *"the tracked `.claude/settings.json` enables `just-module-creator@just-dna` from a `directory`
marketplace at `"./"`, so sessions here run this checkout."* That holds for the MCP server: its process is
`uv run --no-dev --project /data/sources/just-module-creator …`, and it announces v0.48.2. It does not hold for
the skills. `Skill("just-module-creator:create-module")` loaded
`~/.claude/plugins/cache/dna-seq/just-module-creator/0.47.0/skills/create-module/SKILL.md`. The cause is that
`~/.claude/settings.json` also enables `just-module-creator@dna-seq` in **user** scope, which
`installed_plugins.json` records as 0.47.0, beside two local/project entries for -lite (0.43.0, 0.48.0). Two
plugins with one name are both on, and the host took the skills from one and the server from the other.

Today the two skill trees differ in one paragraph: `module-publish/SKILL.md`'s line that 0.48.0's server saves
the environment's token at start. So a seat here reads skills one release behind the server it is testing.
After the next skill change, the tester probes a tool against instructions that no longer describe it, and
the lead's edits to `skills/` never reach the sessions in this clone. The two-installs hazard is the one memory
`local-marketplace-copy-is-not-live` records.

Not ours to fix in code, and not the tester's to change: the user-scope enable is the person's setting.
Candidates: disable `@dna-seq` in user scope and enable it per project where the released plugin is wanted
(-lite already does); or say in §11 that the skill half is not pinned. A guard could check
`Skill`'s base directory against the server's version at start, but nothing in the plugin sees which copy the
host loaded skills from, so that is a host gap rather than ours.

## F126 — `registry_register` says it grinds a new install-id when omitted; it reuses the environment's or the saved one first

**Found:** 2026-08-11 as an unfiled note (live: the result said `install_id_origin: "environment"`); checked
again on 0.48.2's code, 2026-11-07 · **Severity:** low · **Status:** open. Not re-run live: the polygon answers
502, and re-registering would reissue `sheep`'s key.

The docstring: *"omitting `install_id` grinds one for you … calling again without one silently creates a
different account."* `auth.py` (the install-id resolver beside `registry_register`) takes the argument, then
`JMC_INSTALL_ID`, then **the saved account's** (0.47.0: *"A later register with no install-id reuses the saved
one"*), and grinds only when all three are empty. On any machine that has registered once, both sentences are
false. The consequence runs the opposite way from the warning: an agent avoids the call for fear of orphaning
the account, or pastes the live secret in to be safe, when omitting it would have reused the account. A second
note from August belongs with it: the result echoes the install-id back even when it came from the environment
or the saved account, which writes an existing secret into the transcript. `install_id_origin` without the value
says everything the caller needs.

## F132 — upstream text that names a CLI command reaches the agent with no mapping to this surface

**Found:** 2026-11-07 by the tester as F125's second instance (HTT probe); split out by the lead 2026-11-08 ·
**Severity:** low · **Status:** open, `unattended` (the lead's)

`validate_module` and `compile_module` pass on the closure warning's
*"Run `just-dna-compiler close <spec-dir>`"* where this surface has `close_module`. Any upstream text that names a
CLI command reaches the agent unmapped, not only the drafters' flags.

Measured 2026-11-08 on the installed 0.7 packages: about twenty distinct `just-dna-compiler …` /
`just-dna-enricher …` commands are quoted in upstream message text, most of them lane builds
(`clinvar build`, `pubmind build`, `strchive build`, …) whose equivalent here is `provision_caches(lanes=[…])`,
plus `close`, `compile`, `enrich`. F100's `_translate` maps three drafter flags; nothing maps a command, and
nothing touches `to_findings`. Shape of the fix: one CLI-command-to-tool map in `src/`, guarded by a test that
enumerates upstream's typer commands (both directions, as
`test_every_enricher_check_command_has_a_tool_or_a_written_reason` does), applied where upstream text crosses
(`to_findings`, the drafters' warnings, `_translate`) as our own field beside the verbatim message, never
spliced into it: a `source="upstream"` message must stay upstream's. A structured remedy key from upstream would
replace the map's text matching; that ask is the liaison's to weigh.

## F121 — when the seats restart together, every one of them starts without the plugin, and stays without it

**Found:** 2026-11-07, by the tester seat, twice in one day · **Severity:** medium · **Status:** open, a
surface item: each repair below is a decision.

The plugin runs from this checkout, and every seat session starts its own server with
`uv run --no-dev --project . just-module-creator stdio`. Claude Code gives a server 30 s to answer
`initialize`. When the machine is quiet, the server answers in 7.7 s. Measured at 14:40 UTC: the sync
check takes 0.03 s, `import just_module_creator.server` 2.2 s, and `build_server()` 2.4 s. That is about
4× headroom, and both real restarts used all of it:

- **13:51 UTC**: every repo's sessions and watchdogs restarted at once (the kit's pin moved to v0.1.140).
  The liaison's server timed out (`a85b4db8`). The tester's session started at 13:58 and never tried: it has
  no connect log at all, because the host keys a cached failure to the project.
- **16:22 UTC**, after a reboot (kernel 7.2.12 → 7.2.15): the lead (`a8d51777`), the tester (`4d89cf0e`) and
  the liaison (`a85b4db8`) resumed within two seconds of each other. All three of this server's connects
  timed out at 30 s, on a cold page cache with three imports of the toolchain running at once.

The host message says *"retries automatically in 15 min"*, and no retry was logged in 46 min. A session cannot
type `/mcp`, so until v0.1.141 of the seats kit (`watchdog.sh reload --mcp`) the person was the only way back.
The cost is a whole unattended stretch spent by every seat without the product, which is exactly when the seats
are meant to work. The logs are under
`~/.cache/claude-cli-nodejs/-data-sources-just-module-creator/mcp-logs-plugin-just-module-creator-just-module-creator/`.
They record the host's side only: no server stderr, so where the 30 s went is not recorded.

Candidate repairs, none applied, each with its cost:
- **Raise `MCP_TIMEOUT`** in the clone's tracked settings. This is one line. It hides a start that has become
  slow, and it is the person's setting, not ours.
- **Answer `initialize` before importing the toolchain** (lazy imports behind the listing). This wins the race
  under any load, but the tool listing is generated from the live models, so the listing itself would still
  wait. It also sits against the "never an inline import" rule (§2), so it needs a decision first.
- **The kit retries a failed server at resume** (`reload --mcp` from the resume hook). This repairs it for every
  repo, so it belongs on the kit's issues if it is wanted.

**Lead, 2026-11-07:** the third is filed as kit #300 (the resume hook queues `reload --mcp` for a seat whose
plugin server failed, or spreads one clone's resumes). The first is the person's setting and the second needs
§2 reopened, so neither is taken while the kit's answer is pending. Until then a seat that finds the server
missing runs `watchdog.sh reload --mcp` itself (kit v0.1.141).

## F86 — LitVar2 is the rsID↔CAID bridge we lack, and it is DEFERRED to upstream's 0.7

**Not a defect. A probed capability, parked deliberately on 2026-09-01** so the notes are not
re-measured. Upstream is building it as **`RM167`**; the right move here is to consume theirs rather
than ship a second client. **Do not start this without checking `RM167`'s state first** — and check
the *installed* package, not their tree.

> **Checked 2026-09-03: BUILT in their `0.7` branch, and NOT installable.**
> `enricher/src/just_dna_enricher/litvar.py` exists on branch `0.7` with 31 tests, a recorded fixture
> slice and a `just-dna-enricher litvar coverage` CLI command. **But 0.7.0 is in-tree only** — the
> newest tag is `v0.6.6`, PyPI's newest is `0.6.6`, and `from just_dna_enricher import litvar` raises
> in our venv. This is §8's *fixed in tree ≠ released* state, so nothing can be wrapped yet.
>
> **It covers everything below and more.** `LitvarClient` is the reusable primitive: `node(id)` returns
> the raw record where `clingen_ids` lives (rsID → CAID), `allele_node(caid).rsid` goes the other way,
> `pmids(node_id)` is the literature axis, and `gene_nodes(gene)` wraps the repr route through
> `ast.literal_eval`. Both of our corrections are independently theirs, and their `LITVAR_API_BASE`
> comment records the same wrong-base trap costing them two hours.
>
> **Two things a consumer must not assume.** The field is `clingen_ids` **plural** on `variant/get`
> and `clingen_id` **singular** on `autocomplete`; `LitvarNode.parse` reads only the singular, so
> `position_node(rsid).clingen_id` is `None` and the conversion runs through `node()`'s raw dict —
> which their docstring states outright. And their entry point `check_literature_coverage` is a
> **coverage checker that writes an attestation and no rows**, not a conversion tool: it answers
> *allele-resolved / position-only / absent* per locus. The client is what we would wrap; the pass is
> not.
>
> **No overlap with our 0.30.0 work.** Their `ClingenAlleleClient.resolve()` is CAID → coordinates;
> our `lookup_allele_identity` is HGVS → CAID. Opposite directions, and both are wanted.

**Why it was worth probing at all.** `lookup_allele_identity` (0.30.0) answers *what allele does this
HGVS name*, in CAIDs. `lookup_variant` answers *what is at this rsID*. **Nothing joins the two**, and
LitVar2 does: `variant/get/litvar@rs1801133##` returns `clingen_ids: ["CA170990"]` beside the rsID,
the gene, `hgvs: c.677C>T` and `1:11796321`. That is the conversion the identity work left open, plus
a literature axis — 8,951 PMIDs on that rsID, variants indexed *as mentioned in papers*, which a
keyword search does not reach.

**What the probe established, all against the live service:**

- **The base URL is `https://www.ncbi.nlm.nih.gov/research/litvar2-api`.** The `bionlp/litvar2/api`
  path 404s; `bionlp/litvar/api/v1/` exists, is a *different* Django app, and its `entity/` routes
  502 or time out. Its `health/` answers `{"healthcheck": "OK"}` while `entity/search` is down, so
  **that health endpoint does not cover the routes anyone would call.**
- **A LitVar id has SLOTS**, `litvar@<clingen_id>#<rsid>#<gene_id>`, unfilled ones collapsing to a
  bare `#`. So `litvar@rs1800562##` is the **position** node and `litvar@CA113795#rs1800562##` is the
  **allele** node beside it — two records, not one id with a suffix. Reading the trailing `##` as
  decoration is the misreading upstream's own earlier draft made, and it produced the opposite
  conclusion about whether the source is adoptable.
- **The tiers answer differently and the answerable tier is a property of the locus.** BRAF
  `rs113488022` carries three CAIDs — three ALTs at one position. HFE `rs1800562`'s allele node
  returns `clingen_ids: None` and `data_clinical_significance: None` where its position node returns
  both.
- **`data_clinical_significance` is position-level only.** Populated on position nodes, `None` on
  every allele node measured. It is a verdict channel, and it is **not usable as an allele
  authority** — on a multi-allelic rsID it is not a claim about the author's allele. It would also
  land in `clin_sig`, which `enricher.clinical.verify_clin_sig` checks against ClinVar, so writing it
  from here makes that check compare a convention against itself.
- **`variant/search/gene/<GENE>` returns line-delimited Python `repr()`** — single-quoted keys —
  under `Content-Type: application/json`. `.json()` raises `JSONDecodeError`. MTHFR: 1,526 lines.
  The other endpoints are well-formed JSON. **Pinned before anyone writes a client.**
- **`variant/get/<id>/publications` returns `{pmids, pmcids, pmids_count}`** — bare id lists, 8,951
  and 4,585 for `rs1801133`. Corpus-sized, and a PMID list is not a table kind.

**Terms are NCBI's policy rather than a licence**, so there is no `licensing.csv` row to write from
it and no gating axis to declare — which is itself a thing to state rather than leave blank.

**Status (2026-09-25): partly addressed.** 0.7 is installed now (enricher 0.7.2, `just_dna_enricher/litvar.py` under `.venv/site-packages`), and the coverage pass is wrapped as `check_literature_coverage` (`tools/checks.py`, commit `c8c1076`). The rsID↔CAID join through `LitvarClient.node()` / `allele_node()` is still not on our surface: `lookup_allele_identity` goes from HGVS to CAID only.

## The 2026-08-31/09-01 round: what four runs asked for, and how many asked

Four authoring runs, two papers, two builds (0.27.0 and 0.28.0). Every one was asked the same
usability question at the end. **These are corroborations on findings that already have ids, not new
ones** — the count is the point, because a gap four independent runs hit is a different priority from
one a single run mentioned.

| Asked for | Runs | Finding |
|---|---|---|
| A way to read rows out of a downloaded `.xlsx` | **4 of 4** | `F68` — every one hand-wrote a zip+XML parser or reached for `uv run --with openpyxl`; no spreadsheet engine exists in the venv (`openpyxl`, `pandas`, `xlrd` absent, `polars.read_excel` has no backend) |
| `lint_rows` taking a path instead of CSV text | **4 of 4** | `F66` — files were 79–129 KB; two runs skipped the taught `lint_rows → validate_module` step entirely rather than round-trip the table through the model |
| `lookup_citation(doi=…)` to return a title | **4 of 4** | `F113` — upstream `S113`, in pending-fixes |
| A trait CURIE **search**, not just verification | 3 of 4 | `F79` / `F29` — one run guessed four EFO ids, all four obsolete, before finding the live one |
| `registry_check` not reporting `study_count: 0` when the file failed to parse | 3 of 4 | `F60`-adjacent; three-valued rule, `null` is the honest answer |
| `review_queue` showing a real `authored_value` | 3 of 4 | `F71c` — confirmed unchanged |
| An earlier warning than `registry_check` for the `curator`/0.6.1 refusal | 2 of 4 | `F77` — both runs correctly refused to drop the column |
| A liftover, or any warning that the paper is GRCh37 | 2 of 4 | `F73` — cost one run 40% of its module |
| `list_supplementary`'s Europe PMC rung to return URLs that resolve | 2 of 4 | `F114` |

Both have their own entries now: `F113` (in `just-dna-format-pending-fixes.md`) and `F114` (resolved, in `previous_issues.md`).

## F82 — the dogfooding loop burns its own benchmark papers, and the fixture cannot be un-briefed

**Found by a run flagging it against its own interest, 2026-08-31.** A benchmark run on the
centenarian paper reported, unprompted, that `skills/module-curate/GUIDE.md` names **the paper it had
just been given**: *"Measured on PMID 41057961 … `rs61849494` is `chr10:51613269 G/A` on GRCh37 and
`chr10:45982565 C/T` on GRCh38 — 5.6 Mb apart and strand-flipped"*, plus *"Two independent runs met
this on the same paper and both excluded 47 rows."* `skills/module-start/GUIDE.md:130` carries the same
variant. So the run's two headline decisions — rsID-only identity, and excluding the coordinate-only
variants — were **pre-briefed by artifacts of earlier runs on the same paper**, not independently
reached. It said so itself and separated them from the catches that were genuinely its own.

**This is structural, not an oversight.** §7 says to finish each dogfooding probe as a committed
reference example that names what it broke, and the skills are where a measurement becomes guidance.
The benchmark corpus is made of the papers those probes ran on. So **every paper this project learns
from ends up in the guidance the next run reads**, and a fixture is burned as an unbriefed measurement
the moment its lesson is worth keeping. The two are the same pipeline pointed in opposite directions.

**The repair is not to mask the skill.** Masking would break §2's real-identifiers rule and gut a
worked example that is product — and the guidance is *correct*, which is why it is there. Nor is the
repair to stop writing measurements down. What changes is the claim a centenarian score may carry:
`assets/benchmarks/centenarian/metadata.json` now records `pre_briefed: true` with the two skill
locations, so its runs measure **guidance-following** (`F81`'s narrower claim) rather than unbriefed
authoring. Run-to-run agreement remains measurable, because the briefing is constant across runs.

**What it costs, stated rather than designed around.** An unbriefed fixture has to be a paper the
skills have never seen, and it stays unbriefed only until somebody writes down what it taught. There
are three papers in the corpus; `sirt6` is where the adjudicated reference lives and its answer cell
reached `CLAUDE.md` (see the runbook's pitfall 1), and now `centenarian` is briefed in two skills.
**Budget a fresh paper per round rather than expecting the corpus to keep.**

## F79 — the CURIE verifier turns a wrong guess into a confident wrong answer, because nothing finds one

**Found:** 2026-08-31 · **Severity:** medium · **Status:** ours to build, deferred as `RM28` with the
reason recorded there.

`lookup_identifier` verifies a trait CURIE you already hold. Nothing produces candidates, and its own
docstring says writing an id from memory is the failure it exists to prevent — so the only source of a
candidate is the thing the tool forbids. A run guessed four times: `EFO_0007796` is "parental
longevity", `EFO_0007797` is "language measurement", `HP_0025153` is "Transient".

**The first guess is the finding.** "Parental longevity" is a real, current EFO term, so
`lookup_identifier` answers `current` — a green verification of a CURIE naming a different trait, with
nothing in the answer able to say so. That is a check that cannot fail for the error actually being
made. The id the module carries, `OBA_VT0005372`, was reached only through the **obsolete**
`EFO_0004300`, whose record names its successor.

**Surface it rather than patch it.** Making `lookup_identifier` return near-misses would blur verify
and search; a hardcoded map of common traits is the hardcoded-vocabulary defect. The tool is a
search against OLS4, which `check_identifiers` already reaches — `RM28`. And whatever ships must
**report** obsoletion rather than filter on it: the obsolete record was the only one that led anywhere.

## F66 — `lint_rows` echoes its whole input back, and that is load-bearing

**Found:** 2026-08-21, run 2 · **Severity:** low · **Status:** open, deliberately not changed.

`lint_rows` returns the entire input as `normalized_csv`. On a twelve-row slice that is
fine; on a 1,039-row module it doubles a response that is already the largest thing the
tool returns, and the run's ask was to make it opt-in.

**Left as it is, and the reason is the `alterations` list beside it.** The tool reports
what it normalised — `-2.0` written back as `-2` — and a caller applying those needs the
normalized text to apply them *to*. Defaulting the echo off would leave `alterations`
describing edits against bytes the caller no longer has, which trades a size problem for a
correctness one.

The size complaint is still real. The shape that would resolve both is a flag that returns
the normalized rows **only where something was altered**, which is neither the whole file
nor nothing — recorded here rather than built, because it is a behaviour change and this
pass was scoped to surfaces.

## F64 — the plugin cannot see the channel a whole family of modules is published on

**Found:** 2026-08-21, run 2 · **Severity:** medium · **Status:** open, acknowledged.

`compare_to_published`, `registry_is_published` and `registry_search` all answer about the
module registry. Six of `just-dna-lite`'s modules have been published for months on
HuggingFace at `just-dna-seq/annotators`, where each carries a `manifest.json` today, and
that is where that repo's discovery tier actually reads modules from.
`registry_is_published` returns `free_to_publish: true` for them. That verdict is true
about the registry and **false about the world**, so for every module in that repo the
question a revision pass opens with cannot be asked at all.

The plugin is careful about precisely this class of mistake one level down — `target` is
required with no default on every catalog read, because a search that guessed would answer
confidently about the wrong instance. The same argument applies to which *kind* of
publication is being asked about, and there it is not applied. The minimum their run asked
for is the right shape: say what was not looked at.

---

## Probes not yet run

Recorded so the gaps in *this* file are visible too, per the completeness rule.

- **Re-probe `F100` and `F101` on a current server** (both fixed 2026-09-20, now in
  `previous_issues.md`). The tester's stdio server stayed on 0.35.0 for the whole run, so neither fix
  has been exercised by the seat that found it: scaffold with `rows=0` → `draft_from_cpic` on a fresh
  spec, and `check_pgx` / `check_clinpgx` on one of the ClawBio modules under
  `data/interim/clawbio_pgx/modules/`. Needs a fresh session or a `/mcp` reconnect.
- **Run `enrich_expression_effects(rows=true)` against the live Atlas** (`F105`, 2026-09-24). The
  window loop is tested with the upstream call replaced; a real run on a small module is the missing
  half.
- **Author a real module end to end and publish it.** Everything up to
  `compile_module` has been exercised on a real spec; `enrich_module` and
  `registry_publish` have not ([RM4](ROADMAP.md)). This probe would also hit F1
  from the inside rather than by inspection.
- **A binning module — partly run, 2026-08-11.** Probed at the `lint_rows` level
  with real HTT CAG repeat bins (≤26 normal / 27–35 intermediate / 36–39 reduced
  penetrance / ≥40 full penetrance, plus the `unresolved` sentinel). The bounds
  handling held up better than expected: the coverage check reports a genuine hole
  (`no bin covers (26.0, 36.0)` when a bin is missing) and correctly does **not**
  invent one between adjacent integer bins 26 and 27, and the missing-sentinel
  warning states the contract outright — a consumer with no measurement selects the
  sentinel, never the lowest bin. What it did find is [F14](just-dna-format-pending-fixes.md)
  (`S18` upstream): a ragged row is silently shifted and misdiagnosed. **Still not
  run:** scaffold → validate → compile on a binning module, and `heteroplasmy.csv`,
  the other endpoint convention, where bins genuinely do share a bound on a
  continuous measure.
- **`enrich_module` and `registry_publish`, end to end against the live services.**
  Was tracked as a roadmap item until 2026-08-11; it is a probe, not a
  deliverable. The offline ceiling keeps the suite hermetic, so neither can be a
  normal test — what fits is a marked, opt-in integration run alongside authoring
  a small real module all the way through. `registry_publish` needs a token, a
  namespace and a module we are willing to publish immutably; the new
  `published.json` receipt is what makes the result inspectable afterwards.
  **Unblocked 2026-08-11** — `registry_register` now mints the token from inside the
  surface ([F12](previous_issues.md)), and `registry_namespace_available` answers the
  namespace question without spending the irreversible claim to ask it
  ([F13](previous_issues.md)). Both are wrapped and covered offline; **neither has
  been driven against the live service to the point of creating anything**, which is
  precisely what this probe is for.

  **Unblocked differently on 2026-08-11, and this is the bigger change:** the registry
  now runs a *polygon* (`REGISTRY_MODE=test`), where a publish is a rehearsal that
  `registry_delete_version` frees again — version number and content claim both. The
  reason this probe kept being deferred was that it demanded "a module we are willing to
  publish immutably"; on the polygon it demands nothing of the sort. Run it there, with
  `target="test"`, as many times as it takes. Two caveats to carry into it: the polygon
  scopes `duplicate_content` to the publishing account, so a rehearsal cannot prove a
  cross-account duplicate would be refused; and as of filing the polygon host answers a
  bare 404 (DNS'd, app not deployed), so the probe waits on that deployment rather than
  on us.
- **A module with two of something the examples show one of.** The worked example
  throughout is a single-gene, single-rsID module. A paralogous rsID mapping to
  several loci, or one gene carrying two variants with different thresholds, is
  where a key that works for one instance stops working.

## F22 — `published.json`, the receipt we tell the author to commit, records `owner: null`

**Found:** 2026-08-11, rehearsing `test-sheep/fto_bmi@1.0.0` · **Severity:** low · **Status:** open

`registry_publish` says *"Identity recorded in published.json; commit it with the spec"*, and the file
it writes carries:

```json
{ "target": "test", "canonical_id": "test-sheep/fto_bmi@1.0.0", "owner": null, … }
```

`owner` is null in both the tool result and the committed receipt. The registry does know it — a
`registry_get_module` on the same module one call later reports `"owner": "sheep"`, and
`registry_claim_namespace` had already returned `{"namespace": "test-sheep", "owner": "sheep"}`. So the
value was available on the claim and is absent from the publish payload we persist.

Low severity because nothing depends on it and `canonical_id` carries the namespace, from which the
owner is recoverable via the registry. Worth fixing because the receipt's whole job is to be the local
record of what was published where, and "who published it" is a field it declares and then leaves
empty — a reader cannot tell an unowned module from a dropped field.

Probably the same root as `F15` (no enumerated client-surface contract for the registry client): the
publish response shape is read defensively and `owner` may simply not be on it. If so the fix is to fill
the receipt from the claim/whoami we already hold rather than from the publish response — but confirm
where the null originates before choosing, because `research.py::_module_card`'s defensive projection is
deliberate and must not be tightened on the strength of undated client docs.

**Related payload inconsistency, same call, not filed separately:** the top-level `resolution` block
reports `sources: ["clinvar"]` with a signature, while `versions[0].resolution` reports `sources: []`
and `signature: null` for the same version. Ours is the read side only; noting it here so the next
reader of that payload does not treat the nested copy as authoritative.

**Status (2026-09-25): still open, cause located.** The null comes from the model. Installed format 0.7.0's `just_dna_format.manifest.Identity` has no `owner` field (`namespace, name, version, version_coerced_from, canonical_id`), so `_record_receipt`'s `getattr(identity, "owner", None)` is always `None`. To fill it, take the owner from `registry_whoami` or the claim, not from the publish manifest.

## F25 — nothing reports the resolved contact address or which step supplied it

**Found:** 2026-08-11 · **Severity:** low · **Status:** open

The polite-pool contact resolves `JMC_USER_EMAIL` → `JUST_DNA_CONTACT_EMAIL` →
`settings.DEFAULT_CONTACT_EMAIL`, and no tool answers which one won — or whether the author is on the
shared project default at all. `build_services` logs the origin at `debug`, which no MCP client sees.

That matters because `skills/create-module/SKILL.md` now instructs an agent to ask the author for an email
**only when nothing is configured**, and the only way to establish that is to read `.env` off disk — a step
outside the tool surface, in a file that also holds tokens. It is the shape `F23` had before 0.5.4
closed it (see [previous_issues.md](previous_issues.md)): a documented procedure whose precondition the
product cannot report. That one was closed by upstream giving us the check; this one has no upstream half
— the address is ours to report.

**Candidate fix:** surface it read-only on an existing result rather than adding a tool — the origin string
`build_services` already computes (`"JMC_USER_EMAIL"` / `"JUST_DNA_CONTACT_EMAIL"` / `"project default"`)
on `literature_search`'s `sources` block or alongside `lookup_open_access`'s findings, where an agent is
already looking when it matters. **Never the address itself** on a tool result: the origin answers the
question, and echoing a configured address writes personal data into a transcript for no gain — the same
argument as the `registry_register` install-id echo already noted in `UX_TESTER.md`.

## F29 — `lookup_identifier` can verify a trait CURIE but nothing can find one, so the honest routes are luck

**Found:** 2026-08-12, authoring `assets/longevity_2026` · **Severity:** medium · **Status:** open

`describe_table` says `trait_efo_id` takes an "EFO/MONDO/OBA/HP trait ontology id", and
`lookup_identifier` exists precisely so the id is checked rather than recalled — its own docstring says
"writing an ontology id from memory is the failure this exists to prevent."

**But it only answers a closed question.** Given an id it returns current / obsolete / absent with a
label. There is no call that goes the other way, from "human longevity" to a CURIE. So an author who
does not already hold the id has three options, and two of them are the thing the tool exists to stop:

1. recall one and check it — the check passes or fails, but the *recall* is the forbidden step, and a
   plausible wrong id that happens to be `current` passes;
2. leave the column blank — legitimate, and it loses the one machine-readable trait key the row has;
3. go outside the surface to OLS4, which is what "a capability the tool lacks" means.

**What actually happened here was luck, and it is worth writing down because it will not repeat.**
Guessing `EFO_0007796` returned `current` with label `parental longevity` — a real, current term for a
*different* trait, which is exactly failure mode 1 rendering as a pass. Guessing `EFO_0004300` returned:

```json
{"state": "obsolete", "current": "OBA_VT0005372", "label": "obsolete_longevity"}
```

The obsolescence pointer named the replacement, `OBA_VT0005372` ("life span determination trait"), and a
second call confirmed it `current`. **The module got a correct CURIE because a guess happened to land on
a deprecated term.** Had `EFO_0004300` been merely absent, the honest outcome was an empty column.

**The `label` field is the thing to lean on, and half a search already lives in it.** It is what turned
`parental longevity` from a pass into a rejection. A `lookup_identifier(kind="trait", label="longevity")`
returning candidate ids with their labels — reporting, never writing, like every other lookup here —
would close this without touching the refusal model: the author still reads the labels and chooses, and
`trait_efo_id` is not redundancy-bearing, so nothing downstream is made vacuous by it.

**Why not just leave it blank.** Blank is honest and we say so everywhere. But `check_identifiers`
reports traits alongside genes, `registry_get_module` surfaces them, and a trait key is how two modules
about the same phenotype are ever going to find each other. A column that is empty because the surface
cannot help you fill it is a different thing from one that is empty because nothing was stated.

---

## F34 — every publish uploads the previous version's `published.json`

**Found:** 2026-08-12, upstream's review of a publish (theirs to notice, ours to own) ·
**Severity:** low · **Status:** open

**One thing upstream noticed that we did not.** `gather_spec_files` uploads our own `published.json` on
every publish, so each version's storage carries the previous version's receipt. We are the ones who
tell authors to commit that file beside the spec, so the loop is ours to have spotted. Harmless, and
still something shipping that nobody chose.

**The process lesson is the expensive one.** `F27` was already in this repo, filed hours earlier by
another session, with the upstream number on it. This session found the same defect, wrote a fresh
`S7` against the registry, and got it closed as a duplicate of `S5`. The rule that would have caught it
— *"check whether it is already filed first"* — is in `CLAUDE.md` §8 and neither session ran it. Filing
fast is right; filing without reading `docs/` first is how the same note gets written twice.

## F44 — the full network pre-flight cannot tell a module whose every quote is the article's title from one where the quotes are honest

**Found:** 2026-08-20, remediating `aggression_anger`'s quotes on the polygon · **Severity:** high ·
**Status:** open, and narrowed 2026-08-21 · **Upstream:** `S54` and `S56` both **released in 0.6.5**
— the pass reports `titles_as_quotes` (which we surface on `LiteratureReport` as a warning naming the
PMIDs) and warns when a stale quote counter disagrees with `studies.csv`.

**What is still open is this entry's own subject: the pre-flight.** `registry_check` runs the
literature pass on the *server*, and what comes back is a verdict, not the pass's warnings — so the
new signal reaches an author who runs `enrich_literature_pass` locally and not one who runs the most
expensive check on the surface — twice over, since both live instances were still serving
`format: 0.6.1` on 2026-08-21 and the server runs its own pass, not ours. `RM17`'s local check is what covers the second author today, from the
authored file and with no network. The measurement below is the pre-0.6.5 behaviour and is kept as
the record of it.

**The probe.** Two spec directories, identical except for `studies.csv:provenance_quote`:

- `baseline_original` — the module as published: 69 of 69 rows quoted, 3 distinct strings, one per
  PMID, each the article's own title.
- `aggression_anger` — remediated: 1 row carries a passage located in the article's Discussion that
  names that row's variant, 68 are empty on purpose.

Both were put through `registry_check(target="test", literature=true, strict=true)` — the most
expensive check on the surface, the one that runs the literature pass over the network, ~20 s each.

**What came back, both times:**

```
verdict: true      blocking: []      non_blocking: []      unchecked: []
```

Byte-for-byte the same answer. The literature pass ran (the elapsed time says so) and produced no
finding, no counter and no mention of quotes in either direction. `validate_module(strict=true)` and
`compile_module(strict=true)` are equally silent — their warnings on the remediated module were the
deprecated `sources.csv` spelling and the missing closure, and nothing else.

So an author who does the most careful thing the tool offers, and reads the result honestly, learns
nothing about the one column that carries the module's evidence. That is how 3668 title-quotes
reached production through this workflow without anybody being careless.

**`lint_rows` is silent too, and its silence has a shape.** Three rows carrying the *same* title
string, pasted straight in:

```
errors: 0   warnings: 0
findings: 6 × info — chrom, start, ref, doi, p_value_num, provenance_regex
              "left to the author on purpose: … comparing it against a source"
```

`provenance_quote` is absent from that list only because those `info` findings name the
redundancy-bearing columns you left **empty**. Fill it with anything at all — the article's title
included — and the linter stops mentioning it. The one thing it will never say is that the same
string is in every row.

**Why upstream's two notes do not close this one.** `S54` asks the compiler to reject a quote equal
to `CitationHint.title`; `S56` asks it to notice that `literature.csv` disagrees with `studies.csv`.
Both are right and neither is ours. But `registry_check` is *our* projection of the registry's dry
run, it is what the skill tells an author to run before publishing, and its docstring says it
"checks what nothing offline can". A pre-flight that says `verdict: true` and nothing else, on a
module whose entire evidence layer is metadata, is a green light we issued.

**The cheap detector needs no pass at all**, which is the part that makes this ours to build: group
`studies.csv` by `pmid`, count *distinct* non-empty `provenance_quote` values, and report any PMID
with exactly one across many rows. That is offline arithmetic over an authored file. It belongs in
`lint_rows` and in `validate_module`, beside the other authored-table findings, at `warning` — a
repeated quote is a signal, not a malformed module.

**Two candidate repairs that are wrong.**

- *Wait for upstream.* `S54`'s fix lands inside `_study_quote_found`, which — per `S56` — never runs
  on the modules that have the problem. Our check reads the authored file directly and does not
  care whether any pass ran.
- *Refuse the publish.* One quote per PMID is legitimate when a module cites a paper for one row.
  The signal is one quote across *many* rows citing it, and even then a warning is the honest level:
  the author may have chosen a trait-level grain deliberately and said so.

**What was done meanwhile.** Nothing in code — this is the finding, not the fix. The skill half
shipped: `find-evidence` now carries "what may honestly go in `provenance_quote`" with the shape
detector in it, and `studies.md` carries the measurement as its first gotcha.

**Status (2026-09-25): partly addressed.** The "nothing in code" line above is out of date. `authored_checks.repeated_quote_findings` (RM17) reaches `lint_rows` and `validate_module` as a `just-module-creator` finding. Still unverified: whether `registry_check`'s server-side verdict mentions quotes at all. Its result is still the projected verdict and nothing else.

## F45 — no tool writes an authored cell, so no authoring move can go through the log that policy requires

**Found:** 2026-08-20, editing 69 `provenance_quote` cells · **Severity:** high · **Status:** open

`CLAUDE.md` §2's counterstance has three parts, and the second is *"every authoring move goes
through the log… there's a whole `logs/` surface for this and I would want to have every authoring
move going through any tool logged"*, with the corollary *"a move the agent makes by hand is harder
to capture, so make it go through a skill that logs"*.

**There is no such tool and no such skill.** The write surface is `scaffold_module`, the drafters,
the enrich passes, `compile_module` and `close_module`. Not one of them writes a cell an author
chose. So the central authoring act — deciding what goes in a cell and putting it there — happens
entirely outside the product, and therefore outside anything that could log it.

**Measured by doing it.** Replacing the quotes meant `uv run python` with a `csv.DictWriter`, driven
by hand. Per §7 that is the exercise stopping: I stepped outside the product, and I am recording it
rather than presenting the script as a method. The log entry the policy asks for
(`logs/quote-remediation.log`) I then *typed*, which is exactly the "harder to capture" case the
corollary predicts — nothing verified it against what actually changed, and nothing would have
noticed if I had written a different number.

**What a fix looks like, and the ordering matters.** The smallest honest thing is not a general cell
writer. It is a tool per *decided* authoring move, each of which appends its own log line: for this
case, something like `write_provenance_quote(spec_dir, rsid, pmid, quote|null, located_by, reason)`
that verifies the quote is verbatim in the retrieved text before writing, refuses a string equal to
the article's title, and appends to `logs/`. That is small, it is auditable, and the log becomes a
record of what happened rather than a note about it.

**Why the general version is wrong.** A `write_cell(table, row, column, value)` tool would put the
same tooling behind a `weight`, a `clin_sig` and a `conclusion` — the values §10 says an agent must
put in the decision list rather than write. The write surface should widen one *decision* at a
time, not one *column* at a time.

**Status (2026-09-25): partly addressed.** `record_override` (RM16) logs a hand edit to `logs/authoring.log`, and `prune_rows` (`F104`, 0.39.0) is the first write tool shaped around a decision: it applies an author's keep-list and logs it. No tool writes a `provenance_quote` or checks it against the fetched text before writing, which is the tool this entry proposed.

## F107 — a session's MCP server dies mid-run when `uv sync` swaps its venv, and nothing says so until the next call

Same day, on the session that adopted fastmcp 4. The plugin's server process imports lazily, so
after `uv sync` replaced fastmcp 3 with 4 under it, every tool answered *No module named
'fastmcp.server.tasks.routing'* — a message about a package, from a tool the caller asked about a
module. `/reload-plugins` fixes it and the rule is simply *reload after a sync*; the finding is that
the error names nothing the caller can act on. The workaround that let the run continue is worth
keeping: a forty-line script that builds the server in-process and drives tools through
`fastmcp.client.Client(server, mode="legacy")` is the whole product surface without the host, and
it is what the unattended run used for every call above.

**Status 2026-09-24: documented, not fixed.** `SYMPTOMS.md` now maps the message to the cause and to
`/reload-plugins`, so an agent that looks it up has the repair. The message itself is unchanged: a
middleware translating `ModuleNotFoundError` would run inside the same swapped environment and can
fail the same way, so it is not worth building on a guess. The durable fix would be a host-side
notice that the plugin's venv changed — a Claude Code / Codex behaviour, not ours.

## F111 — a published card says 24 quotes were read and missed when none could be checked (upstream `S109`)

**Found:** 2026-09-24, reading back `test-sheep/test_late_onset_alzheimers_kunkle2019@0.1.0` ·
**Severity:** medium · **Status:** format-tree `S109` accepted 2026-09-24 as their `RM256`, which is
on their `0.8` branch — close on that release; its root on the fetch side is `S110` (`F108`).
**2026-09-27:** format 0.7.1 (installed) shipped only RM264, the descriptions: `quotes_found` and
`quotes_unchecked` now send a reader to `abstract_only_count`. The shape is kept for 0.7.x, so
`skills/module-publish/SKILL.md`'s read-back step now carries the sentence.

`enrich_literature_pass` reported `quotes_unchecked: 24`. The manifest it fed reports
`quotes_found: 0, quotes_unchecked: 0`, because an abstract-only row stores `quotes_found=0` rather
than null, and the compiler counts only nulls as unchecked. Our tool reports the pass's own number,
which is right. The published record doesn't match it, and only `abstract_only_count: 1` beside it
says why. Nothing to change on our side. `module-publish`'s read-back step is where an author would
notice, so if upstream keeps the shape, add one sentence there.

## F135 — triage's gene-on-the-wrong-chromosome check cannot run in the order `module-start` teaches

**Found:** 2026-11-09 by the tester, layman probe (`data/interim/probe_layman_mthfr/`) · **Severity:** medium ·
**Status:** open

`module-start`'s triage puts "**The tell for a generated claim is a real gene name beside an invented rsID**" at
step 2: *"`check_identifiers` answers it: read `gene_locus_conflicts`"*. Its step 0 sets the safe default for
any handed source, rows authored with an **rsID only**. The probe followed both. A machine-written summary named
`MTHFR A66G (rs1801394)`, whose rsID is real but in MTRR on chromosome 5. On three rsid-only triage rows,
`check_identifiers` answered `gene_locus_conflicts: []` with `gene_locus_check_skipped: "no coordinates authored
and no resolution.csv beside the spec"`. After `enrich_module` (1 min 49 s, rows resolved from the cache) the
same call caught it: *"rs1801394 is on chromosome 5, but HGNC puts MTHFR on chromosome 1"*.

So the check works, but at the step that names it there is nothing for it to read. The skill's own rule saves
an attentive agent (*"If `gene_locus_check_skipped` is non-null the comparison never ran"*). Neither the skip
reason nor step 2 says what produces the missing input, and the router's order (curate, then enrich) puts
`resolution.csv` two stages after triage. A layman's agent that reads "skipped" as "nothing to see" carries the
generated pairing into curation. Shape of a fix, the lead's call: the skip reason names `enrich_module` (or a
`lookup_variant` per rsID) as the way to get coordinates, and step 2 says to enrich the triage rows first.
Alternatively, `check_identifiers` resolves rsid-only rows' chromosomes itself from the local Ensembl lane,
which `lookup_variant` already reads.

The conflict message also guesses the wrong half: *"a real symbol beside an invented rsID"*, when here both are
real and the rsID belongs to another gene. Naming the gene the rsID does sit in would settle it in one line.

## F136 — `lookup_variant` prints every PubMind record twice, and its first call takes minutes

**Found:** 2026-11-09 by the tester, layman probe · **Severity:** low · **Status:** open

On `rs1801131` the answer lists 29 PubMind records twice, once in full under `pubmind` and once as `withheld`
advisories, each with the same redundancy note. That is about 15 kB, where the verdict (ClinVar's call, the
locus, and one warning that PubMind disagrees with itself) is a few hundred characters. `check_identifiers`
already settled this shape: verdict first, roster behind `detail=true`. The `withheld` entries for PubMind could
collapse to one entry with a count, as `literature_search` does for DOIs ("Withheld for the reason given on the
first withheld row").

Timing, from the host's log: three `lookup_variant` calls issued together on a fresh server finished together
after **2 min 43 s** each, all `answered_by: local`. One more call on the warm server took **9 s**. The
first-call cost looks like the snapshots being opened, not per-call work, but nothing in the answer or the
docstring warns that the first lookup is slow, and the host moved all three to the background at 120 s.

## F137 — remove a table and its sidecars keep the removed rows; validate, compile and audit all stay quiet, and the manifest attests them

**Found:** 2026-11-09 by the tester, layman probe · **Severity:** medium · **Status:** open

The probe triaged three handed rsIDs in `variants.csv` and ran `enrich_module`, then dropped one (rs1801394, the
MTRR variant the summary had called MTHFR's). After reading the papers it removed `variants.csv` altogether,
because the finding is a two-variant pair (`haplotypes.csv` + `diplotypes.csv`). Both moves were logged with
`record_override`. The spec dir still held what the triage enrich wrote: `resolution.csv` with **all three**
rsIDs, including rs1801394 on chromosome 5, plus `clin_sig_concordance.csv` and `clin_sig_authority_calls.csv`.

`validate_module(strict)` passed with no word about it. `compile_module(strict)` passed and hashed that
`resolution.csv` into `manifest.derived` and `resolution_signature`. No parquet carried rs1801394: the
orphan-present and orphan-removed compiles had the same `artifact_digest` (`9427a3f9…`) and `content_signature`
(`62794c0c…`), and only `resolution_signature` and the `derived` hash moved. So the artifact's data is clean,
but the manifest attests a resolution table that names a variant the author dropped as a generated claim. A
spec-dir upload (`registry_publish`, `remote_derive`) would carry the file. That last part is unverified,
because the polygon has answered 502 throughout. `audit_module` didn't see it either. `enrich_module`'s note does
say *"To regenerate resolution.csv after changing the spec you must DELETE it first, or stale rows persist
silently"*. That covers a re-run, but nothing tells an author who **removed** rows or a table that the derived
files now carry subjects nothing authored. The pass that wrote them is the only party that could know.

This is computable offline: a sidecar row whose subject (`variant_key`/`rsid`) appears in no authored table. It
is an audit signal (ours, `audit.py`), and arguably a compiler warning (upstream's, for the liaison to weigh).
The repair has to be `refresh_sidecar`, which captures before it deletes, never a silent prune. Reproduce:
scaffold `variants.csv` with three rsid-only rows, run `enrich_module`, delete one row (or the table), then
`validate_module` and `compile_module`. Both stay quiet and `resolution.csv` keeps the row. The probe dir no
longer shows it, because `refresh_sidecar` was run there (below).

## F138 — `audit_module` reads a stale `verification.json` as current, and never reads `diplotypes.csv`'s directions

**Found:** 2026-11-09 by the tester, layman probe · **Severity:** low · **Status:** open

On the same spec dir, `validate_module` and `compile_module` both say *"verification.json is stale: the
attestation was computed over different module bytes … nothing here describes the rows being compiled"*.
`audit_module`'s `checks_that_never_ran` reads that same file and reports *"9 of 13 recorded check(s) compared
nothing"* as a decision about this module, with no mention that the records describe bytes that no longer
exist. The fix is to check the attestation's digest first, as the compiler does, and report the signal
`not_computed` (why: stale) rather than `decide`.

Second, `directional_claims_without_studies` answers *"variants.csv is not here, so no row could be read"*,
while `diplotypes.csv` carries `direction=risk` on two rows. `clinical_claims_without_studies` already reads
diplotypes (*"activity_phenotype.csv, copynumbers.csv, diplotypes.csv, …"*), so the directional signal is the
narrower of the two for no stated reason. For a diplotype module it is always `not_computed`.

**F137, the repair route, on the same spec dir.** `refresh_sidecar(sidecar="resolution.csv")` is the right tool
here, and it worked: capture verified, 3 rows → 2, rs1801394 left in the capture as `only_in_capture`, nothing
put back. But it reads the result the wrong way. Its `next_step` says *"The fact signature MOVED. If nothing was
reapplied and nothing conflicts, that is the source having changed its answer"*, and its warning says nothing
proves *"a human wrote them rather than the source having withdrawn them"*. Ensembl withdrew nothing: the
**author** removed the subject from every table. The canary has three causes, not two: the source moved, the
author edited a cell, or the author removed the subject. It can tell the third apart, because the subject is
absent from every authored table, and should say so. Otherwise an author who just dropped a row reads that the
source changed its mind.

## F139 — a re-attestation re-signs checks it did not re-run, so an old check's verdict is stamped onto new bytes

**Found:** 2026-11-09 by the tester, layman probe · **Severity:** high · **Status:** open; the writer is
upstream's (enricher 0.7.3), to be filed through the liaison

`verification.json` holds one record per check with its own `checked_at`, under one `module_hash` and one
signature for the whole file. On the probe spec dir:

1. 02:38 UTC, `check_identifiers` over 3 triage rows writes `gene_locus_agreement: subjects 3, findings 1
   (rs1801394/MTHFR)`.
2. The author drops rs1801394, then removes `variants.csv` for haplotypes + diplotypes. `validate_module` now
   calls the file stale (*"computed over different module bytes"*). That is correct.
3. 02:45 UTC, `enrich_module` writes the file again: `module_hash` = the **current** bytes, a fresh signature,
   and its own records re-run. `gene_locus_agreement` is carried over unchanged (`checked_at` 02:38,
   `subjects: 3`).
4. `compile_module(strict)` no longer warns of staleness. It reports *"verification.json records 1 finding(s)
   … gene_locus_agreement (1 of 3)"* as `carried` (no edit clears it), and it will publish that finding for a
   module whose tables no longer name rs1801394. `check_identifiers` now refuses to re-attest (*"no
   variants.csv — the check does not apply … no verification.json was created"*), so nothing on the surface
   can retire the record.

That direction publishes a false finding. The other direction is the dangerous one: a clean `gene_locus_agreement`
(or trait, PGS, CIViC record) from an earlier pass is re-signed over rows added after it ran. The manifest then
attests a check that never saw those rows, and the file's `module_hash` says it did. Per-record `checked_at`
survives, but nothing compares it, and the signature covers the file.

Shape of a fix, upstream: a carried record keeps the hash it was computed over, and the compiler reads such a
record as stale per check. Ours meanwhile: `audit_module` could flag records whose `checked_at` predates the
file's newest authoring edit (logs/authoring.log has the times), and a check that no longer applies should
remove its own record rather than leave it.
