# logo.{png,jpg,jpeg} — the module's picture, and the house style it is drawn in

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

Not a table. No CSV, no parquet, no pydantic row model. It is a single optional image beside the
spec, and it is in this set because it is the one authored file whose *content* nothing validates —
the compiler checks its extension and hashes its bytes, and after that every question about it is a
question about taste. So this file is half mechanics and half style guide, and the style half is
reverse-engineered from the nine hand-drawn logos that actually shipped.

Everything below was measured on **format / compiler 0.6.1, enricher 0.6.4, registry 0.18.2**
(the live instances, probed 2026-08-19). Probes are marked *measured*.

---

## What it is

The picture a catalog card shows instead of a generic glyph. A module may ship
`logo.png` / `logo.jpg` / `logo.jpeg` next to `module_spec.yaml`; the compiler copies it into the
artifact and hashes it into `manifest.logo` as `{name, sha256, size}`. That entry sits **outside
`artifact.files[]` and outside `artifact.digest`**, which is the whole design: swapping the picture
is a PATCH on an immutable registry, never a new content identity, and the registry has a dedicated
amend endpoint that spends no version number. When there is no logo, consumers fall back to
`display.icon` + `display.icon_set` + `display.color`
(`just_dna_format.manifest:1437-1443`, `:132`).

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.manifest.FileEntry`, held as `ModuleManifest.logo: FileEntry \| None` (`manifest.py:1437`) |
| Accepted names | `logo.` + an extension in `manifest.LOGO_EXTENSIONS` — `frozenset({"png","jpg","jpeg"})` (`manifest.py:46`). Ask the constant, not this line |
| Parquet it becomes | **none.** It is copied verbatim into the output directory and hashed; no columnar form exists |
| Natural key | the filename. One logo per module, per version |
| Authored or machine-produced | **authored** — or agent-drawn. Nothing in the toolchain generates one |
| Who writes it | a human or an image agent, into the spec dir. Never the compiler, never an enricher pass |
| Fact signature | none — it is not a fact table |
| In `content_signature`? | **no** (*measured*) |
| In `artifact.digest`? | **no**, and not in `artifact.files[]` either (*measured*) |
| In `artifact.files[]`? | no. Only parquets are. `manifest.logo` is its own top-level field |
| Discovery | `_collect_logo` (`compiler.py:620-647`): explicit `logo_file=` argument, else the first `logo.<ext>` for `ext in sorted(LOGO_EXTENSIONS)` — **`jpeg`, then `jpg`, then `png`** |

## Who populates what

There is one cell, and one decision behind it.

- **author** — the image file itself, and the fallback trio it competes with (`display.icon`,
  `display.icon_set`, `display.color`) which stay authored in `module_spec.yaml` whether or not a
  logo exists. `manifest.RECOMMENDED_COLORS` / `RECOMMENDED_ICONS` (`manifest.py:70-95`) are a
  *recommendation only* — `color` is validated by `COLOR_PATTERN` and `icon` is free-form within
  `icon_set`.
- **compiler-stamped** — `manifest.logo.{name,sha256,size}`. Tolerates nothing authored: the field
  is not part of the spec DSL at all, so there is no authored value to overwrite. `sha256` carries
  the `sha256:` prefix (`file_entry`).
- **registry-stamped** — on `amend_logo` the server *renames* the uploaded file to `logo.{ext}`
  regardless of what it was called (`registry/services/publish.py:706`) and rewrites
  `manifest.logo` in stored storage. It also re-projects `logo_url` onto the card
  (`services/catalog.py:36-39`).
- **nobody, ever** — there is no `logo_alt_text`, no `logo_width`, no `logo_license`. See
  *What does not exist*.

**Which cells no tool may fill even though it easily could.** None here, and that is worth saying
explicitly rather than leaving as an absence: the logo carries no redundancy and no attestation,
so `hints.REDUNDANCY_BEARING` and `hints.ATTESTATION_BEARING` have nothing to say about it. A logo
is decoration; no cross-check ever compares it to anything. Which means the *only* thing that keeps
a module's picture honest is the person who drew it — there is no refusal here to lean on.

## What moving this asset moves

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| Adding a logo where there was none | unchanged (*measured*) | n/a | unchanged (*measured*) | unchanged |
| Swapping the image bytes | unchanged | n/a | unchanged | unchanged |
| Renaming `logo.png` → `logo.jpg` | unchanged | n/a | unchanged | unchanged |
| Adding a *second* logo (`logo.jpeg` beside `logo.png`) | unchanged (*measured*) | n/a | unchanged (*measured*) | unchanged — but `manifest.logo` flips to the jpeg, silently |
| Deleting the logo | unchanged | n/a | unchanged | unchanged |
| Recompile under a newer toolchain | unchanged | n/a | may move for other reasons | unaffected by the logo |

*Measured how:* `reference_examples/apoe_epsilon` copied three ways — no logo, `logo.png`, and
`logo.png` + `logo.jpeg` — and compiled with `compile_module(..., resolve_with_ensembl=True)`.
All three produced `artifact.digest = sha256:11f69653b56ae328…` and
`content_signature = sha256:343333b67741bec0…`. Only `manifest.logo` and the out-dir file list
differed.

1. **Is it inside `content_signature`?** No. `content_signature` covers the authored *spec* — the
   yaml and the CSVs — and a picture is not a claim about a genome. Nor is it a derived table with a
   fact signature; it has no facts.
2. **Is it inside `artifact.digest`?** No, and unlike every other out-dir file it is not in
   `artifact.files[]` at all (*measured*: `artifact.files` on the probe was exactly
   `['haplotypes.parquet','diplotypes.parquet']`). This is the one out-dir asset whose bytes move
   neither hash — the README is the same shape, and logs and `provenance.json` are its siblings
   (`docs/audit/COMPILER_FROM_CODE.md:228-237`).
3. **Does an edit here un-close the module?** No. The attestation binds the authored *inputs*
   (`compiler.authored_input_entries`), and the logo is not one. A closed module stays closed
   through a logo swap — which is exactly why `amend_logo` can exist on an immutable registry.
   Note the asymmetry with an `authorship:` append, which un-closes a module while moving no
   identity at all; the logo moves neither.
4. **Is it part of the canary?** No. Content-unmoved-but-fact-signature-moved is a reading about
   upstream sources re-answering a question. The logo asks no question.

## Required to exist

Nothing requires it. It drags in nothing. A module with no logo is a complete, publishable,
signable module, and — *measured on the live production catalog, 2026-08-19* — **all five published
modules have `logo_url: null`**, so today the no-logo path is the only path anyone has walked
recently.

What the logo *is* required to be: an extension in `LOGO_EXTENSIONS`. Anything else raises
`ValueError` inside `_collect_logo` at **compile** time (`compiler.py:641-642`) — though the
exception does not reach you: `compile_module` catches it and returns
`CompilationResult(success=False, errors=[str(exc)])`, so a bad extension **fails the compile**
rather than raising out of it. `validate_spec` never
opens it — `docs/audit/COMPILER_FROM_CODE.md:616` lists "provenance / logo / readme validation" as
*error at compile, not checked at validate*. Nothing anywhere checks that the bytes are an image;
a text file named `logo.png` compiles, hashes and publishes.

## The decisions that carry judgement

- **Whether to ship one at all.** A logo is the difference between a card that looks like a product
  and a card that looks like a row in a database. But an ugly or off-theme one is worse than the
  `display.icon` fallback, which is at least consistent with every other module.
- **`display.icon` / `icon_set` / `color`.** These are what a viewer sees when the logo is absent,
  fails to load, or is on a surface that does not fetch images. They stay meaningful even when a
  logo ships, so do not treat them as dead once you draw one. `icon_set` is a live vocabulary
  (`VALID_ICON_SETS`) — ask for it, do not recall it.
- **Extension.** Pick `png`, always, and see the two traps below. `jpeg` in particular is quietly
  half-supported downstream.
- **The picture itself.** Not a schema question. See *The house style*.

## The house style

Derived by **opening fourteen image files and looking at them** — the nine hand-drawn logos in
`/data/sources/just-dna-lite/data/interim/v1_port/*/logo.png`, plus five distinct machine-drawn ones
under `data/modules/generated/` and `data/output/generated_modules/` (six files; `latest_longevity`
appears twice, byte-identical).

The nine hand-drawn ones are not samples — they are exactly the nine logos that were published, byte
for byte: their sha256s match `manifest.logo.sha256` in
`/data/sources/just-dna-registry/data/mirror/just-dna-seq/*/‹version›/manifest.json` (e.g. cardio
`sha256:3ed8ec7ee29d…`, vo2max `sha256:4daacafff694…`). That mirror is a 2026-08-08 pull of the old
0.9.1 deployment; those nine modules are **not** on the live registry today.

### What all nine share — the invariants

| Trait | Value, measured |
|---|---|
| Format | PNG, 8-bit, **RGBA** — every one carries a real alpha channel |
| Canvas | 601–606 × 541–547 px. Aspect **1.104–1.113**, i.e. ~10:9. **Never square** |
| Background | fully transparent outside the mark. All four corners are `(255,255,255,0)` in all nine |
| Silhouette | one large circle, outer diameter **498–503 px** ≈ 92% of canvas height |
| Ring stroke | **17–18 px**, ≈ 3.6% of the circle's diameter (mid-height scan of thrombophilia and lipidmetabolism) |
| Corner mark | a second, smaller circle at the **top right**, breaking the big circle's outline, stroked in the same colour, holding the same 3D rainbow-ribbon DNA render — green/cyan/yellow/blue backbones, scattered red dots, white field. **Present in all nine.** This is the family mark |
| Subject | one illustration in the upper half, left of and under the corner mark |
| Text | present in all nine: bold sans, 1–3 lines, centred, in the **lower half, inside the ring** |
| Ink coverage | the mark fills **82–86%** of the frame bounding box |
| Rendering | flat fills for ring, text and background. No gradients on the frame, no drop shadow, no bevel |

### What varies — do not copy these as rules

- **Ring / accent colour, one per module.** `#4053a4` indigo (cardio, coronary, pathogenic,
  vo2max) · `#0feaa6` spring green (superhuman, thrombophilia) · `#57afce` light blue
  (lipidmetabolism) · `#e6391c` red (cancer) · `#f07e1f` orange (longevitymap).
- **Interior treatment**, four different answers: opaque white (cardio, coronary, pathogenic,
  vo2max — 36% of pixels transparent, i.e. outside the ring only) · fully transparent
  (lipidmetabolism 64%, thrombophilia 60%) · a solid `#3188b5` teal-blue disc (cancer, longevitymap
  — 34% of all pixels are that one colour) · a photographic fill (superhuman, and only superhuman).
- **Text colour follows the interior**: white on a filled disc, `#317ec2` or `#155289` on white or
  transparent.
- **Literal vs symbolic.** Six are literal-anatomical stock clip-art: a heart (cardio, coronary),
  lungs (vo2max), blood vessels (thrombophilia), dividing cells (cancer), a lipid droplet
  (lipidmetabolism). Two are symbolic-molecular: a stylised helix (longevitymap, pathogenic). None
  is abstract.
- **Shading inside the subject.** The frame is flat but the clip-art is not always — the lipid
  droplet runs `#fdc357` → `#fee7bb` → `#fdcf79`, the cancer cells `#f7a7a8` / `#d07676`.
- **A second helix beyond the corner mark** appears in only two of nine. The corner mark is the
  helix motif; a helix *in the subject* is optional and, on this evidence, a minority choice.
- **Wording.** Five say "Major risks (X)"; the rest are a plain noun phrase. That prefix belongs to
  a v1 product family, not to the style.

### What none of them ever does

No square canvas. No opaque rectangular background. No gradient on the ring or the field. No drop
shadow, glow or 3D bevel on the mark. No wordmark outside the circle. No photo-realism except
superhuman's single photographic fill. No frame-filling helix as the only subject.

## A prompt that reproduces it

Fill in the two braces and hand this to an image agent.

> A flat vector circular badge logo for a genetics annotation module about **{SUBJECT}**.
> Composition: one large open circle centred in the frame, its ring drawn as a clean solid stroke in
> **{ACCENT_HEX}** at about 3.5% of the circle's diameter, the circle occupying roughly 92% of the
> canvas height. Inside the upper half, a single simple medical-illustration subject representing
> {SUBJECT} — flat vector, minimal shading, no outline noise. Inside the lower half, the module
> title on 1–3 centred lines in a bold geometric sans, coloured to contrast the interior. At the
> top-right, overlapping and breaking the large circle's outline, a small second circle stroked in
> the same **{ACCENT_HEX}**, with a white field, containing a colourful 3D-rendered DNA double helix
> — green, cyan, yellow and blue backbones with small scattered red dots. Everything outside the
> large circle is fully transparent. Flat colour throughout; no gradients on the ring or the
> background, no drop shadow, no bevel, no glow.

**Negative list** (each item is something all nine avoid): no square or rectangular canvas · no
opaque or coloured background fill behind the badge · no gradient ring · no drop shadow, outer glow
or 3D bevel · no photorealism · no text outside the circle · no watermark or signature · no
helix as the sole subject · no neon / cyberpunk palette · no clutter behind the mark.

**Fixed constraints, taken from the real files and not invented:**

- PNG, 8-bit **RGBA**. The alpha channel is not optional — it is the one trait all nine share and
  none of the machine-drawn ones has.
- Canvas ≈ **601 × 542** (10:9). Square is wrong for this family, though see the caveat below.
- Everything outside the badge fully transparent (alpha 0).
- The mark should occupy **≥ 80%** of the frame's bounding box. It is rendered at 20–28 px.
- File name exactly `logo.png`.

### Does the existing logo-drawing agent match this? No — and here is exactly how it diverges

The agent is **`generate_logo`**, a tool on the module-creator PI/solo agent in
`/data/sources/just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/agents/module_creator.py:592-609`,
backed by `_generate_logo_image` (`:497-518`) which calls
`NanoBananaTools(api_key=…, aspect_ratio="1:1").create_image(prompt)` — Gemini native image
generation, the "nanobanana" tool from `agno.tools.nano_banana` (`:44`). Its instructions live in
`agents/prompts/pi.yaml:226-239` and `agents/prompts/module_creator.yaml:196-208`, in both cases as
step 7/9 of the authoring order, with the same worked example:

> "A glowing double helix wrapped around a heart filling the entire frame edge-to-edge, deep purple
> and teal gradient, flat vector style, no background whitespace, no margins."

Seven divergences, in descending order of how much they matter:

1. **Alpha is destroyed unconditionally.** `_autocrop_whitespace` opens the image with
   `.convert("RGB")` (`:474`) and re-exports from that. There is no path through this tool that
   produces a transparent PNG. *Measured*: all six generated files are PNG color-type RGB with no
   alpha; all nine hand-drawn are RGBA. This is the single biggest gap, and it is a four-character
   fix in one line.
2. **The prompt asks for none of the four invariants** — no circular ring frame, no shared
   rainbow-helix corner medallion, no in-ring title text, no transparency. Those four are what make
   the nine look like one family.
3. **It asks for a "gradient"** (`pi.yaml:233-234`). The house style is flat.
4. **The autocrop cannot fire on a coloured background.** It thresholds against `255 - 20 = 235`, so
   on an image whose field is darker than that the whole frame differs and `getbbox()` returns the
   full frame. *Measured* on `data/output/generated_modules/recent_longevity_2024/v1/logo.png`
   (corner RGB `(72,104,73)`): bbox `(0,0,1024,1024)`, 100% of frame, nothing croppable.
5. **The stated render size is wrong.** The prompt says "displayed as a tiny 48px thumbnail"
   (`pi.yaml:231`). The real consumer renders it at **20 px** (`webui/pages/registry.py:452`),
   **22 px** (`:243`) and **28 px** (`:899`), always `objectFit: contain`.
6. **`aspect_ratio="1:1"`** is forced square against a 10:9 family. Under `objectFit: contain` this
   only letterboxes, so it is the least harmful item on the list.
7. **The output has 80–87% dead margin.** *Measured* ink bounding boxes on the five white-field
   generated logos: 13%, 15%, 20%, 20%, 20% of frame, against 82–86% for the hand-drawn set. **Be
   fair about this one**: all six generated files predate commit `ee6a68a` (2026-03-19 20:21), which
   introduced `_autocrop_whitespace`, so they show what the *prompt alone* produces — not a broken
   crop. Items 1 and 4 are code-level certainties; this one is evidence that the prompt does not
   carry its own instruction.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **Two logos on disk is silent, and `jpeg` wins.** Discovery iterates
   `sorted(LOGO_EXTENSIONS)` = `['jpeg','jpg','png']` (*measured on the installed package*), so a
   spec dir holding both `logo.png` and `logo.jpeg` compiles with `manifest.logo.name = "logo.jpeg"`
   and no warning at all (*measured*: the probe's `manifest.logo` was the jpeg, `logo.png` was not
   even copied to the out dir). Compare `licensing.csv` / `sources.csv`, where two spellings of one
   sidecar is a hard `layout.SidecarCollision` — the logo gets no such protection. **Keep exactly
   one logo file, and make it `logo.png`.**
2. **`validate_module` never looks at it.** A wrong extension, a zero-byte file, a PDF renamed to
   `.png` — none of it surfaces until `compile_module`, and only the extension surfaces even then
   (as a compile *failure* — `_collect_logo`'s `ValueError` is caught and returned as
   `success=False, errors=[…]`). A green strict validate says nothing about your logo.
3. **`verify` catches a swapped logo only if you ask, and never catches a missing one.**
   `verify_manifest(..., check_logo=True)` on a substituted image raises
   `IntegrityError: logo hash mismatch …` (*measured*), but the default is `check_logo=False`
   (`integrity.py:408`) so an ordinary verify passes a tampered logo. Worse, the check is guarded by
   `if path.is_file()` (`:539`) — *measured*: deleting the logo entirely and re-running with
   `check_logo=True` returns cleanly. A download that lost the file verifies green while the
   manifest attests it.
4. **`reverse_module` throws it away.** The function takes no logo parameter at all
   (`compiler.py:6052-6064`) and `docs/audit/COMPILER_FROM_CODE.md:695` states it plainly: "Logs,
   `provenance.json`, logo and readme are not re-emitted." So `compile → reverse → compile` loses
   the logo without touching the digest — the round-trip *looks* perfect and the picture is gone.
5. **`logo.jpeg` does not survive the enricher's HuggingFace upload.** `upload.py:61-62` allowlists
   `logo.png` and `logo.jpg` only, and the comment at `:47` calls it out: "`logo.jpeg` is a
   pre-existing instance of that same skew, left alone here because widening it is not this item's
   decision." Publish a `.jpeg` logo to HF and the manifest attests a file the repo does not carry.

   **Fixed in enricher 0.6.6** (upstream **RM105**): the publisher's logo allowlist now derives from
   `LOGO_EXTENSIONS`, the way the readme half already derived from `README_CANDIDATES`, so the
   spelling the compiler *prefers* is no longer the one the upload dropped. **If you published a
   module carrying a `logo.jpeg` before that release, re-publish it** — the manifest attested bytes
   the repository did not carry, and nothing in `verify_manifest(check_logo=True)` catches an absent
   file. Discovery order is deliberately unchanged: it still sorts `LOGO_EXTENSIONS`, so **`jpeg`
   beats `jpg` beats `png`** and a spec directory holding two logos still ships the jpeg and does not
   even copy the loser. **Keep exactly one logo in the spec directory** — that half was never the
   bug and is not fixed.
   The registry does not share this hole — `gather_spec_files` uploads everything that is not a
   parquet.
6. **`amend_logo` renames your file.** Upload `heart-v3.png` and it is stored as `logo.png`
   (`registry/services/publish.py:706`). Do not expect your name back.
7. **The corner medallion is not in any package.** The one bundled logo asset in the tree is
   `just-dna-pipelines/src/just_dna_pipelines/v1_port/data/logos/vo2max.png` — a single fallback for
   one module, byte-identical to the published vo2max logo, not a template kit. There is no
   distributable of the rainbow-helix mark, so an agent reproducing the house style has to
   re-draw it.

## What does not exist

- **No `logo` key in `module_spec.yaml`.** You cannot name the file; it is discovered by convention
  or passed as a Python argument (`compile_module(..., logo_file=…)`, `compiler.py:3900`). The
  compiler CLI has no `--logo` flag — grepping `compiler/src/just_dna_compiler/cli.py` for "logo"
  returns only `--check-logo` at `:217`.
- **No SVG.** `LOGO_EXTENSIONS` is raster-only. No transparency-preserving vector path exists, and
  `amend_logo` returns `422 invalid_logo` for anything else.
- **No alt text, no dimensions, no logo licence field.** `FileEntry` carries `name`, `sha256`,
  `size` and nothing more. If your logo is someone else's copyrighted artwork, the module records
  that fact nowhere.
- **No second image.** One logo per version. No screenshots, no banner, no icon set.
- **No content validation, ever.** Nothing opens the bytes as an image.
- **No `registry_amend_logo` tool in this plugin.** `just-module-creator` wraps
  `registry_amend_readme` (`tools/registry.py:575`, gated in `auth.GATED_TOOLS:67`) and stops there;
  `references/CLI.md:29` routes a logo fix to the raw `registry-client amend-logo`. Grepping
  `src/just_module_creator/` for "logo" returns nothing at all.
- **`compile_module` here never passes `logo_file`.** This plugin relies entirely on convention
  discovery, which means gotcha 1 applies to every module it compiles.

## Consumption today

Genuinely read, in three places, all in the consumer half:

- `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/annotation/hf_modules.py:212-217` —
  probes `{base}/logo.{png,jpg,jpeg}` in that order and sets `ModuleInfo.logo_url` (`:63`, `:242`).
  The comment at `:237-238` says the probe is deliberate: "neither is in `ARTIFACT_PARQUETS`, so a
  manifest says nothing about them and asking it would drop the logo off every module."
- `just-dna-lite/webui/src/webui/app.py:332-356` — `GET /api/module-logo/{module_name}` serves it
  as a `FileResponse` with `image/png` / `image/jpeg`, guarding `..` and `/` in the name.
- `just-dna-lite/webui/src/webui/pages/registry.py:241-245`, `:450-455`, `:897-901` — renders it at
  22 px, 20 px and 28 px respectively, `objectFit: contain`, `borderRadius` 3–4 px, falling back to
  `fomantic_icon("box", …, "#6435c9")` when absent.

Written, in two:

- `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/v1_port/sources.py:115-139` `fetch_logo`
  — pulls a Gen-I GitHub repo's root `logo.{png,jpg,jpeg}` into the ported spec dir, falling back to
  the bundled `data/logos/<name>.png`. Called from `v1_port/runner.py:92` and
  `v1_port/clinvar_runner.py:106`. **This is where the nine hand-drawn logos come from.**
- `agents/module_creator.py:497-518` — the nanobanana tool, above.

Registry side:

- `registry/services/catalog.py:36-39, 264` — `_logo_url` projects
  `/api/v1/modules/{ns}/{name}/versions/{v}/files/{logo.name}` onto every card
  (`models/api.py:248`). Fetching it does not count as a download
  (`api/routers/modules.py:276`).
- `registry/api/routers/modules.py:266-267, 316-317` — the served-file allowlist and the manifest
  entry list both include the logo when present.
- `registry/services/publish.py:679-715` + `api/routers/publish.py:581-619` — `amend_logo`,
  owner-gated, no version bump. `client.py:758-766` / `client_cli.py:280-293` are the client and CLI
  halves.
- `registry/services/upgrade.py:497-507` — a toolchain upgrade carries the logo forward explicitly
  as "version-independent branding".

**Nothing in `just-module-creator` reads or writes it.**

**And the verdict on real modules: nothing published today has one.** *Measured 2026-08-19* against
both live instances (`registry 0.18.2 / format 0.6.1 / compiler 0.6.1`): production
(`module-registry.just-dna.life`) holds 5 modules — `antonkulaga/aggression_anger_snps`,
`antonkulaga/big_five_personality_snps`, `antonkulaga/cognitive_intelligence`,
`antonkulaga/risk_impulsivity_snps`, `eric-mods/lactose_tolerance` — and every one reports
`logo_url: null`. The polygon holds 0 modules. None of the 16 reference examples in
`just-dna-format/reference_examples/` contains any image file, and neither does
`just-module-creator/assets/`. The only modules that ever shipped a logo are the nine
`just-dna-seq/*` in the 2026-08-08 registry mirror, which were never republished.

## Blanks for just-dna-lite

- **Ask the logo agent to draw to the house style.** Its prompt (`agents/prompts/pi.yaml:226-239`,
  `module_creator.yaml:196-208`) asks for none of the four invariants — ring frame, corner medallion,
  in-ring title, transparency — and actively asks for a gradient the family never uses. Today an
  agent-drawn module is visibly not a member of the set that shipped. The prompt block in this file
  is drop-in.
- **Ask `_autocrop_whitespace` to stop destroying alpha.** `module_creator.py:474` does
  `.convert("RGB")`, so the generation path cannot emit a transparent logo, while every published
  logo is RGBA. It should convert to `RGBA`, compute the bbox from the alpha channel when one
  exists, and fall back to the white-threshold path only for opaque images. It should also refuse —
  or say so — when the field is darker than its 235 threshold, which is the
  `recent_longevity_2024` case where the crop is a measured no-op.
- **Ask `hf_modules` to trust `manifest.logo` and stop probing.** The comment at `:237-238` says a
  manifest "says nothing about" the logo. That was true when only `ARTIFACT_PARQUETS` was attested;
  `manifest.logo` carries `{name, sha256, size}` and has since format 0.5. Today lite serves a
  logo it has not verified while the hash sits unread one field away. Probing can stay as the
  fallback for manifest-less sources; when a manifest is present it should name the file and lite
  should check the digest.
- **Ask for a `logo` slot in the module-card fallback chain to be exercised at all.** With five
  published modules and zero logos, `logo_url` is dead code in production — the icon fallback is the
  only path anyone has tested end to end since the mirror.

## Ask the live schema

There is no `describe_table("logo.png")`; the logo is not a table and the authoring tools have
nothing to say about it. The live answers come from the constants:

```python
from just_dna_format.manifest import (
    LOGO_EXTENSIONS,          # accepted extensions — the only vocabulary here
    VALID_ICON_SETS,          # icon_set values for the no-logo fallback
    RECOMMENDED_ICONS,        # curated icon suggestions (recommendation, not enforcement)
    RECOMMENDED_COLORS,       # curated hex suggestions, by semantic use
)
sorted(LOGO_EXTENSIONS)       # discovery order — first hit wins, so jpeg beats png
```

For the fallback trio as an author sets them, `authoring_reference()` and
`describe_table("module_spec.yaml")` cover `display.icon` / `icon_set` / `color`. For what the
compiler will do with the file, read `_collect_logo` (`just_dna_compiler.compiler:620`) — it is
27 lines and it is the whole contract.
