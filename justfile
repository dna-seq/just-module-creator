# Common tasks. Install `just` (https://github.com/casey/just) or copy the
# underlying `uv ...` commands. Run `just` to list recipes.

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
run mode="essentials":
    JMC_MODE={{mode}} uv run just-module-creator stdio

# Run over HTTP.
serve mode="essentials" port="3011":
    JMC_MODE={{mode}} uv run just-module-creator http --port {{port}}

# Open the MCP Inspector (interactive dev UI).
dev:
    uv run fastmcp dev fastmcp.json

# Load this repo as a Claude Code plugin for one session.
plugin:
    claude --plugin-dir .

# Everything CI would run.
ci: lint types test
