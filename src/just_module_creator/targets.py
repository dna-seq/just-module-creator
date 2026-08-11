"""Which registry instance a call is aimed at, and what each one accepts.

The registry runs **two deployments of one image** (registry 0.12): production —
the catalog everyone installs from — and the **polygon**, an instance started
with ``REGISTRY_MODE=test``. They do not share a database, an account, a
namespace or an artifact store.

The split exists because a published version is immutable *and* its authored data
is claimed by a name-independent ``content_hash`` that ``yank`` does not release.
So on a single instance every rehearsal permanently burns both a version number
and the right to publish that data under any other name. The polygon accepts
``test-``prefixed data and will hard-delete it again; production refuses to
accept it at all.

**Why the write tools default to the polygon.** A forgotten ``target`` there
costs nothing — delete it and go again. The same omission against production is
irreversible. Reads about the published world (searching the catalog,
downloading a module) default to production, because that is the world the
question is about.

**What we deliberately do NOT do:** infer an instance's mode. No endpoint reports
``REGISTRY_MODE`` (filed as ``S3`` in the registry's intake), and the only
available inference — testing whether ``openapi.json`` mounts the DELETE routes —
would make this a second source of truth for something only the server knows. A
target names a *host we were configured with*; it is never a claim about what
that host believes it is.
"""

from __future__ import annotations

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
    """
    if target != "prod":
        return None
    if namespace and is_test_namespace(namespace):
        return (
            f"Production refuses test data: a namespace starting {TEST_NAMESPACE_PREFIX!r} is "
            "`422 test_data_on_prod` there, at the claim as well as at the publish. Rehearse "
            'under this name on the polygon (target="test"), and publish to production under a '
            "name that is not marked as test data."
        )
    if name and is_test_module_name(name):
        return (
            f"Production refuses test data: a module name starting {TEST_MODULE_PREFIX!r} is "
            '`422 test_data_on_prod` there. Rehearse it on the polygon (target="test"); a module '
            "published for real needs a name that is not marked as a test."
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
