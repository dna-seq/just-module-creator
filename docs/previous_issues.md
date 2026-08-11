# Previously resolved findings

Dogfooding findings (`F#`) resolved **here**, each with its resolution and a code
pointer. Findings move into this file from [dogfooding.md](dogfooding.md); they
are not copied.

**Check here before re-investigating a finding that looks fixed.**

---

## F3 — a strict compile failed with no indication of which step was missing

**Found:** 2026-08-11, first end-to-end run · **Resolved:** 2026-08-11

Compiling a complete, valid spec with `strict=True` returned `success: false`.
The spec was fine; it had simply never been enriched, so no `resolution.csv`
existed and strict refuses what it cannot reproduce.

The finding was not the refusal — that is correct — but that our result gave no
signal about *where in the workflow* the caller was. Fixed by surfacing upstream's
`errors` verbatim in `CompileReport` (it names the unresolved variants and says
what to inject) rather than reducing the outcome to a boolean, and by stating the
enrich→compile ordering in `compile_module`'s docstring and in the skill.

Pointer: `src/just_module_creator/tools/authoring.py`, `compile_module`;
`tests/test_pipeline.py::test_strict_compile_refuses_unresolved_rows` pins that
the refusal arrives as structured errors rather than an exception.

## F4 — the test suite could not import its own helpers

**Found:** 2026-08-11 · **Resolved:** 2026-08-11

`from tests.conftest import offline_settings` resolved to a `tests` package
shipped by a transitive dependency inside `site-packages`, not to this repo's
`tests/`. Collection failed with a confusing `ImportError` naming a path in
`.venv`.

Fixed by importing as `from conftest import ...`, which resolves through the
directory pytest puts on `sys.path`. Recorded in `CLAUDE.md` §6 so the next agent
does not "fix" it back.

Pointer: `tests/test_modes_and_auth.py` import block.
