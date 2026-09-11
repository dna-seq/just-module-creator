# Common tasks. **`just` is NOT installed on this box** (`just --version` -> command
# not found, 2026-09-11), so every recipe here is a place to read the underlying
# `uv ...` command rather than something to invoke. Install it
# (https://github.com/casey/just) or copy the line; `just` with no argument lists
# recipes once it is there.

default:
    @just --list

# Install all dependencies (incl. dev) into the project venv.
install:
    uv sync

# Run the test suite (in-memory, offline — no network).
test:
    uv run pytest

# Lint.
lint:
    uv run ruff check .

# Auto-format / autofix.
fmt:
    uv run ruff check --fix .
    uv run ruff format .

# Type-check.
types:
    uv run pyright

# Run the server over stdio (default transport for local MCP clients).
# `JMC_MODE` used to be set here, defaulting to a tier called "essentials". The mode
# axis was removed in 0.21.0 — there is no tier — so the variable was exported and read
# by nothing while naming a concept the surface had dropped.
run:
    uv run just-module-creator stdio

# Run over HTTP.
serve port="3011":
    uv run just-module-creator http --port {{port}}

# Open the MCP Inspector (interactive dev UI).
dev:
    uv run fastmcp dev fastmcp.json

# Load this repo as a Claude Code plugin for one session.
plugin:
    claude --plugin-dir .

# Build manuscript Markdown + PDF from the EASRP LaTeX. The PDF half needs
# `MANUSCRIPT_TECTONIC` pointing at the static build (see CLAUDE.md section 11); without
# it this writes the Markdown, fails, and leaves the previously committed PDF in place —
# which is how a stale page count gets read as a fresh measurement. `--nopdf` is the
# honest form on a host that cannot render.
manuscript:
    uv run manuscript manuscript

# Build the empty EASRP template (Markdown + PDF) to check the toolchain.
manuscript-template:
    uv run manuscript template

# Everything CI would run.
ci: lint types test
