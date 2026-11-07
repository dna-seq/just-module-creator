# Upstream ledger: the two hosts

The plugin runs inside two clients and is primary in neither (CLAUDE.md, the top section): **Claude Code** and
**Codex**. Kept by the liaison seat (`docs/seats/LIAISON.md`). A post upstream in either (an issue, a comment) is
drafted for the person and posted only on their word on that text.

No clone is watched for either. Claude Code's source is not public; its release notes are. Codex
(`openai/codex`) is public, but a watcher on its busy trunk would wake the seat for nothing we use. So each
host's read mark is the version running here, read at each start with `claude --version` and `codex --version`,
and a version past the mark is read from the host's release notes against the list below.

## Read mark

- **Claude Code 2.1.319** (2026-11-07, the version running this seat). No release before it is read: the mark
  starts here, fast-forwarded (the kit's base, "A mark may be fast-forwarded").
- **Codex `codex-cli` 0.166.0** (2026-11-07). The same.

## What the plugin uses

### Claude Code

- `.claude-plugin/plugin.json`: `skills: "./skills"` (every `SKILL.md` a `/`-command, every `GUIDE.md` loaded
  by path); `mcpServers` launching `uv run --no-dev --project ${CLAUDE_PLUGIN_ROOT} …` over stdio.
- `.claude-plugin/marketplace.json`, a `directory` marketplace; the tracked `.claude/settings.json` enables the
  plugin per repository (CLAUDE.md §11). Install is a copy under `~/.claude/plugins/cache/`; `claude plugin
  uninstall / marketplace update / install` is the reinstall (CLAUDE.md §10).
- No hooks, no `commands/` directory (a command file would shadow a skill of the same name; a test refuses it).
- MCP: tool listing size (descriptions are paid context), `ToolAnnotations` in camelCase (SDK 1.x drops
  snake_case), the session lifetime the token store relies on (`auth.session_state_persists`).

### Codex

- `.codex-plugin/plugin.json`: `skills: "./skills/"`; `mcpServers` with `"cwd": "."`, because Codex substitutes
  `${PLUGIN_ROOT}` only in hook commands. It carries the second hand-bumped version.
- Installs from git into `~/.codex/plugins/cache/<marketplace>/just-module-creator/<version>/`, dropping symlinks
  (`AGENTS.md` arrives missing); the first start builds that copy's `.venv` cold. `tests/test_codex_install.py`
  drives the reinstall (CLAUDE.md §11).

### Both

- The MCP wire: fastmcp is pinned `>=3.4.6,<4` because fastmcp 4 negotiates the sessionless 2026-07-28 protocol
  (memory `fastmcp-pinned-below-4.md`). A host release that drops the older protocol versions breaks us there
  first; read each host release for its MCP protocol line.

## What to read in a host release

Plugin manifest fields and their substitution variables; skill discovery and how `SKILL.md` / non-`SKILL.md`
files are listed; MCP protocol versions, session handling and tool-listing limits; install and cache layout.
Everything else is *nothing for us*, listed in one line.
