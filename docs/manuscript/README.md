# Manuscript prototyping

This folder is a scratch workspace for drafting the just-module-creator paper: outlines, LaTeX, figures, and notes we iterate on together. It is not a finished submission and is not the project's durable documentation.

Use it to try section structure, wording, and citations before anything lands in a venue-specific Overleaf project or a camera-ready PDF. Durable writeups stay in `docs/` (`DOMAIN.md`, `CHANGELOG.md`, the skills).

`template.tex` is the European AI Summer Research (EASRP 2026) starter: anonymous 8-page A4 main text, compile with `pdflatex` (or Overleaf) and keep `easrp2026.sty` next to the `.tex` file.

Build Markdown (for editing context) and PDF:

```bash
uv run manuscript template      # template.tex → template.md + template.pdf
uv run manuscript manuscript    # manuscript.tex → manuscript.md + manuscript.pdf
```

# Manuscript writing process

The idea is that we use Claude Code and Cursor to write the manuscript in this repository, with sibling checkouts in the workspace for facts the paper must not invent:

* [just-dna-format](https://github.com/dna-seq/just-dna-format) — schema, compiler, enricher (we wrap these; we own none of them)
* [just-dna-lite](https://github.com/dna-seq/just-dna-lite) — companion platform paper; the consumer that joins a compiled module to a VCF
* the registry checkout on disk (`just-dna-marketplace` is a stale directory name only)

An older draft lived in just-dna-lite as `docs/manuscript/v0.2/paper2-dna-agents.md`. That draft described `just-dna-agents`, which this plugin replaced. Use it for inspiration only. Follow the EASRP section order in `template.tex` / `manuscript.tex` (Introduction, Related work, Method, Results, Discussion, Conclusion). Do not rebuild the agents-paper section list (unified MCP toolkit, Agno team, PRS orchestration).

Papers needed for related work can be downloaded into `data/cache/for_manuscript/` (gitignored with the rest of `data/`).
