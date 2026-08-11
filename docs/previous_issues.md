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

## F12 — the first step of the publishing workflow was not in the tool surface

**Found:** 2026-08-11, asked to create an account and a namespace on the live
registry · **Resolved:** 2026-08-11, 0.3.0

Every registry tool needed a token, and the only route to one the surface named was
`registry-client register` — a shell command in another package, pointed at by
`authenticate`'s docstring. So the plugin gated every registry action behind a
credential nothing in it could mint, and onboarding quietly cost a second toolchain
despite install instructions that promise one command.

Not an upstream gap: `RegistryClient.register(install_id, account)` is public in the
**published** 0.9.1, `POST /auth/register` needs no auth because it mints the token,
`allow_self_register` defaults true (no admin, no email), and
`generate_install_id()` grinds the proof-of-work locally in 0.3–1.2 s. A public
onboarding API we had simply never wrapped.

Fixed by `registry_register(account, install_id=None, difficulty=None)`. Three
decisions worth keeping:

- **It lives in `auth.py`, always on.** It writes to the registry but cannot be
  token-gated — it is what produces the token — and extended-only would have
  reproduced the same dead end behind a mode flag. `CLAUDE.md` §5 now states the
  exception and its test: a registry write is gated *unless the token is its output*.
- **The token goes into the caller's own session slot**, so registering leaves the
  session usable and no secret has to be copied back through the transcript.
  `authenticate` is now only for a token you already hold.
- **Both secrets come back, and the install-id carries the warning.** It is the
  account's only recovery path; re-registering it reissues a key for the same
  account, while registering again without it creates a *different* account and
  strands the first. `JMC_INSTALL_ID` was added so a later session can reuse it,
  which is a value we read and never write — persisting it ourselves would widen the
  write surface. The `account_taken` error says outright that retrying will not help.

Pointer: `src/just_module_creator/auth.py` — `registry_register`,
`resolve_install_id`, `_registration_failure`;
`models.RegistrationResult`; `settings.install_id`;
`tests/test_modes_and_auth.py::test_an_illegal_account_name_is_refused_before_any_socket`
and `::test_install_id_precedence_and_origin`.

**Not verified end to end from this side, deliberately.** The wrap, the local
refusals and the offline ceiling are covered by the suite, and the live service was
exercised read-only plus one real failure path (a deliberately invalid install-id
returning `422 invalid_install_id`, mapped to actionable text). Actually minting an
account and claiming a namespace belong to the dogfooding side — a builder who also
runs the irreversible probe has graded their own work. **A shipped fix is not a
passed probe.**

## F13 — an irreversible claim had no pre-flight, though upstream shipped one

**Found:** 2026-08-11, same session · **Resolved:** 2026-08-11, 0.3.0

`registry_claim_namespace`'s docstring warned that a namespace "is claimed once and
then owns every module published under it, so this is not a step to run
speculatively" — and then offered no way to be non-speculative. The only way to
learn whether a name was free was to try to take it.
`RegistryClient.namespace_available` is public, read-only and needs no token, and
was unwrapped.

Fixed by `registry_namespace_available` in `research.py`, essentials — beside
`registry_search`, which was already the home for token-free registry reads, and in
the default surface because a pre-flight for an irreversible step belongs there.

**`valid` and `available` are returned separately, and the live registry proves why:**
it answers `test_modules` with `valid: false, available: true`. Collapsing them into
one boolean would have told an author that an illegal name was claimable.

The naming half was the sharper finding. Accounts are validated with the *namespace*
rule (`is_valid_namespace`, `^[a-z0-9]+(-[a-z0-9]+)*$`), so `test_creator` and
`test_modules` were rejected before anything else could happen — and our docstring
said only "Lowercase, hyphen-separated", which reads as a style preference rather
than a hard reject. Module names are the opposite rule, `^[a-z][a-z0-9_]*$`, which
is why a spec holds `my-ns/lactose_tolerance`. That asymmetry is now stated in
`registry_claim_namespace`, `registry_register`, `registry_namespace_available`, the
server instructions, the skill and the README, and an illegal account name is
refused locally with the pattern named, before a round trip is spent.

Pointer: `src/just_module_creator/tools/research.py` —
`registry_namespace_available`; `models.NamespaceAvailability`;
`src/just_module_creator/tools/registry.py` — `registry_claim_namespace`'s docstring.
