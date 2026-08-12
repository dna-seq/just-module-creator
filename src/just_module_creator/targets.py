"""Which registry instance a call is aimed at, and what each one accepts.

The registry runs **two deployments of one image**: production — the catalog
everyone installs from — and the **polygon**, an instance started with
``REGISTRY_MODE=test``. They do not share a database, an account, a namespace or
an artifact store.

The split exists because a published version is immutable *and* its authored data
is claimed by a name-independent ``content_hash`` that ``yank`` does not release.
So on a single instance every rehearsal permanently burns both a version number
and the right to publish that data under any other name. The polygon accepts
``test-``prefixed data and will hard-delete it again; production refuses it **by
default** — registry 0.14 added an explicit ``allow_test_data`` override, which
this surface does not expose (see ``prod_refusal``).

**Why the write tools default to the polygon.** A forgotten ``target`` there
costs nothing — delete it and go again. The same omission against production is
irreversible. Reads about the published world (searching the catalog,
downloading a module) default to production, because that is the world the
question is about.

**A target is declared here and verified by the server.** Registry 0.13 reports
``REGISTRY_MODE`` on ``/health`` and ``/api/v1/version``, and
``RegistryClient(expect_mode=…)`` asserts it before the first call that could
spend anything. So ``client_for`` always passes it: our configuration records
which instance we *meant*, and the guard checks which one *answered*. The two are
deliberately separate — we still never infer a mode ourselves, because that would
make this a second source of truth for something only the server knows.

An unreported mode fails the check rather than passing it: a caller who asked for
the deployment to be verified is worse off believing it was than knowing it could
not be. The remedy for that direction is a server upgrade; the remedy for the
other direction is nothing, because the publish already happened.
"""

from __future__ import annotations

from just_dna_registry.client import RegistryClient

from just_module_creator.settings import RegistryTarget, Settings

#: What production refuses and the polygon accepts, in each identifier's own
#: spelling. Namespaces and account handles allow hyphens; a module name is
#: validated ``lowercase alphanumeric with underscores``, so `test-panel` is a
#: 422 at publish and can never exist — one rule, two spellings.
#:
#: These duplicate upstream's ``config.Settings.test_data_prefix`` default and
#: ``services.purge.module_name_prefix``. Duplicated rather than imported because
#: both live in modules outside the client's exported surface, and an import that
#: a future client-only wheel drops would take the whole server down at load time
#: for a cosmetic gain. ``tests/test_registry_targets.py`` asserts the two match,
#: so the drift fails the suite instead of surprising an author.
TEST_NAMESPACE_PREFIX = "test-"
TEST_MODULE_PREFIX = "test_"

#: The default target per kind of question. Not one constant, because the two
#: kinds are asking about different worlds — see the module docstring.
DEFAULT_WRITE_TARGET: RegistryTarget = "test"
DEFAULT_CATALOG_TARGET: RegistryTarget = "prod"


def client_for(
    target: RegistryTarget, settings: Settings, *, token: str | None = None
) -> RegistryClient:
    """A client for ``target``, pinned to the mode that target names.

    **The single construction point, so no call site can forget the guard.**
    ``expect_mode`` costs no request — upstream asserts it lazily, on the same
    calls its version guard already covers (publish, import, download, validate,
    check, is_published) and never on a cheap read. That is why it is passed
    uniformly here rather than only where a guarded method happens to be reached:
    the alternative is a per-site judgement about which upstream method is
    guarded today, which is exactly the kind of fact that goes stale silently.

    ``RegistryTarget`` and upstream's mode share one spelling (``prod`` /
    ``test``), so this passes the target through rather than mapping it.
    """
    return RegistryClient(
        settings.registry_url_for(target),
        token=token,
        timeout=settings.registry_timeout,
        expect_mode=target,
    )


def is_test_namespace(namespace: str) -> bool:
    """Whether ``namespace`` (or an account handle) is spelled as test data."""
    return namespace.startswith(TEST_NAMESPACE_PREFIX)


def is_test_module_name(name: str) -> bool:
    """Whether a *module* name is spelled as test data."""
    return name.startswith(TEST_MODULE_PREFIX)


def describe(target: RegistryTarget, settings: Settings) -> str:
    """``"the polygon (https://…)"`` — for messages that must name the instance."""
    url = settings.registry_url_for(target)
    return f"{'the polygon' if target == 'test' else 'production'} ({url})"


def prod_refusal(target: RegistryTarget, *, namespace: str = "", name: str = "") -> str | None:
    """The reason production will refuse these names, or ``None``.

    A local pre-check, not a replacement for the server's: production answers
    ``422 test_data_on_prod`` on its own and remains the authority. Checking here
    costs nothing and turns a round trip into a sentence that says what to do.

    **As of registry 0.14 the server's ban is a default rather than an absolute** —
    ``allow_test_data=true`` is a documented way through, on publish, import and the
    namespace claim. This surface deliberately does **not** expose it, so the refusal
    below is now partly *ours*, and it says so rather than claiming the server makes
    it impossible. The reason to keep refusing is the one upstream gives for keeping
    the default: the failure is silent and permanent, because a mistyped namespace
    spends a version number and a global ``content_hash`` that only an operator purge
    frees. An agent that can wave that through on an author's behalf is exactly what
    the polygon default exists to prevent.
    """
    if target != "prod":
        return None
    if namespace and is_test_namespace(namespace):
        return (
            f"A namespace starting {TEST_NAMESPACE_PREFIX!r} is refused on production by default "
            "— `422 test_data_on_prod`, at the claim as well as at the publish. The registry does "
            "have an explicit override and this surface does not offer it, because a mistyped "
            "namespace there spends a version number and a global content hash that only an "
            'operator purge frees. Rehearse under this name on the polygon (target="test"), and '
            "publish to production under a name that is not marked as test data."
        )
    if name and is_test_module_name(name):
        return (
            f"A module name starting {TEST_MODULE_PREFIX!r} is refused on production by default "
            "— `422 test_data_on_prod`. The registry has an explicit override; this surface does "
            'not offer it. Rehearse on the polygon (target="test"); a module published for real '
            "needs a name that is not marked as a test."
        )
    return None


def polygon_naming_note(
    target: RegistryTarget, *, namespace: str = "", name: str = ""
) -> str | None:
    """Advice when polygon data is *not* spelled as test data, or ``None``.

    Advice, never a refusal. The polygon accepts an unprefixed name, and
    rehearsing a publish under the exact name it will carry in production is the
    most useful rehearsal there is — it is the last one before going live. What
    the author should know is the consequence: ``registry purge-test-data``
    sweeps by prefix, so an unprefixed rehearsal is not swept and has to be
    deleted by name.
    """
    if target != "test":
        return None
    unprefixed = [
        f"namespace {namespace!r}" if namespace and not is_test_namespace(namespace) else "",
        f"module name {name!r}" if name and not is_test_module_name(name) else "",
    ]
    named = [n for n in unprefixed if n]
    if not named:
        return None
    return (
        f"Note: {' and '.join(named)} is not spelled as test data "
        f"({TEST_NAMESPACE_PREFIX!r} / {TEST_MODULE_PREFIX!r} prefixes), so the operator's "
        "`purge-test-data` sweep will not pick it up. That is fine — a rehearsal under the real "
        "name is the most faithful one — but clean it up yourself with `registry_delete_version` "
        "or `registry_delete_module` when you are done."
    )
