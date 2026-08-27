"""The prod/polygon split: which instance a call reaches, and with whose token.

Three properties are load-bearing here and each has a test that fails loudly:

* **Every registry tool takes a `target`**, so a new one cannot quietly inherit
  a single endpoint.
* **The defaults are asymmetric on purpose** — writes rehearse on the polygon,
  catalog reads ask production — and an accidental flip is the failure this
  whole split exists to prevent.
* **Credentials never cross instances.** The two registries keep separate
  databases, so a production token is not a weaker key on the polygon; it is a
  key for an account that is not there.

The suite stays hermetic: nothing here opens a socket. The refusals under test
happen before any request, which is exactly why they are worth having.
"""

from __future__ import annotations

import pytest
from conftest import offline_settings

#: Everything that speaks to a registry, and which instance it must default to.
#: Writes rehearse; catalog reads ask the published world. `authenticate` is a
#: write in this sense — it stores a credential *for* an instance.
from just_module_creator.auth import (
    GATED_TOOLS,
    unauthenticated_result,
)
from just_module_creator.settings import (
    DEFAULT_POLYGON_URL,
    DEFAULT_REGISTRY_URL,
    RegistryTarget,
    Settings,
)
from just_module_creator.targets import (
    TEST_MODULE_PREFIX,
    TEST_NAMESPACE_PREFIX,
    client_for,
    polygon_naming_note,
    prod_refusal,
)

REGISTRY_TOOL_DEFAULTS = {
    "registry_register": "test",
    "authenticate": "test",
    "registry_whoami": "test",
    "registry_namespace_available": "test",
    "registry_claim_namespace": "test",
    "registry_publish": "test",
    "registry_delete_version": "test",
    "registry_delete_module": "test",
    # Yank is the one write whose real audience is production — a bad publish there is
    # what it exists for. It still defaults to the polygon like every other write: an
    # unaimed yank that silently delisted a production version would be the mistake this
    # tool exists to recover from, committed by the tool itself.
    "registry_yank": "test",
    "registry_unyank": "test",
    # The pre-flights follow the publish they precede: rehearse against the polygon,
    # because a dry run aimed at the wrong instance answers about the wrong catalog —
    # `published_as` is per-instance, so a production duplicate is invisible from the
    # polygon and vice versa.
    "registry_validate": "test",
    "registry_check": "test",
    # A write, so it rehearses like the others — and it is per-instance anyway: the
    # module it amends exists on one registry only.
    "registry_amend_readme": "test",
    # The catalog reads have NO default, and `None` here means exactly that. They
    # defaulted to production until 2026-08-21, which was right about the common case
    # and wrong about the common mistake: rehearse a publish on the polygon, read it
    # straight back, get a 404 from a *different* instance than you just wrote to, and
    # conclude the catalog is broken. A read cannot know which world was meant, so it
    # asks — the enum makes both options visible where the call is written.
    "registry_is_published": None,
    "registry_search": None,
    "registry_get_module": None,
    "registry_download": None,
    # Health follows the write default so the common case — "confirm I am pointed at
    # the polygon before I rehearse" — needs no argument.
    "registry_health": "test",
}


def _no_credentials(monkeypatch) -> None:
    """Say "this environment has no registry token", for all four variables.

    ``setenv(..., "")`` rather than ``delenv``: an empty value is how a test says
    "no credential" to a reader that does ``x or os.environ.get(...)``, and
    ``load_dotenv(override=False)`` skips a key that is merely absent. All four
    because a developer's own ``.env`` must never decide what a test asserts.
    """
    for var in ("JMC_API_KEY", "JMC_TEST_API_KEY", "REGISTRY_TOKEN", "REGISTRY_TEST_TOKEN"):
        monkeypatch.setenv(var, "")


async def _schemas(client) -> dict[str, dict]:
    return {t.name: t.inputSchema for t in await client.list_tools()}


# --------------------------------------------------------------------------- #
# The prefixes are upstream's, and drift is a suite failure rather than a surprise
# --------------------------------------------------------------------------- #
def test_the_test_data_prefixes_match_the_ones_the_registry_enforces():
    """We duplicate two upstream values; this is what stops the copy going stale.

    They are duplicated rather than imported because both live outside the
    client's exported surface — see ``targets`` — so the guard has to be a test.
    """
    from just_dna_registry.config import Settings as RegistrySettings
    from just_dna_registry.services.purge import module_name_prefix

    upstream_prefix = RegistrySettings.model_fields["test_data_prefix"].default
    assert upstream_prefix == TEST_NAMESPACE_PREFIX
    assert module_name_prefix(upstream_prefix) == TEST_MODULE_PREFIX


# --------------------------------------------------------------------------- #
# Endpoints and tokens
# --------------------------------------------------------------------------- #
def test_each_target_resolves_to_its_own_endpoint():
    settings = offline_settings()
    assert settings.registry_url_for("prod") == DEFAULT_REGISTRY_URL
    assert settings.registry_url_for("test") == DEFAULT_POLYGON_URL
    assert settings.registry_url_for("prod") != settings.registry_url_for("test")


def test_a_production_token_is_never_offered_to_the_polygon(monkeypatch):
    """No cross-instance fallback, in either direction."""
    _no_credentials(monkeypatch)
    settings = Settings(_env_file=None, api_key="mk_live_prod")  # type: ignore[call-arg]

    assert settings.registry_token("prod") == "mk_live_prod"
    assert settings.registry_token("test") is None, (
        "a production key on the polygon is an unknown key, not a weaker one"
    )

    settings = Settings(_env_file=None, test_api_key="mk_live_poly")  # type: ignore[call-arg]
    assert settings.registry_token("test") == "mk_live_poly"
    assert settings.registry_token("prod") is None


def test_the_toolchain_env_vars_are_read_per_instance(monkeypatch):
    _no_credentials(monkeypatch)
    monkeypatch.setenv("REGISTRY_TOKEN", "from-toolchain")
    monkeypatch.setenv("REGISTRY_TEST_TOKEN", "from-toolchain-test")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.registry_token("prod") == "from-toolchain"
    assert settings.registry_token("test") == "from-toolchain-test"


async def test_the_session_store_keeps_one_token_per_instance(make_client):
    """Authenticating against one instance must not unlock the other.

    The token lives in FastMCP session state under a key that carries the target,
    so this asserts the key is still two-axis: flatten it and the second
    `authenticate` would silently retarget the first. Driven through the client
    rather than against the resolver, because the store is now the framework's
    and a session is the only thing that has one.
    """
    async with make_client() as client:
        await client.call_tool("authenticate", {"token": "poly-key", "target": "test"})

        prod = await client.call_tool("registry_whoami", {"target": "prod"})
        assert prod.data.success is False
        assert "prod" in prod.data.message

        stored = await client.call_tool("authenticate", {"token": "prod-key", "target": "prod"})
        assert stored.data.authenticated is True
        assert stored.data.target == "prod"


def test_the_two_instances_read_different_http_headers():
    settings = offline_settings()
    assert settings.api_key_header_for("prod") != settings.api_key_header_for("test")


def test_the_unauthenticated_message_names_the_instance_and_its_variable():
    settings = offline_settings()
    prod = unauthenticated_result(settings, "prod")
    test = unauthenticated_result(settings, "test")

    assert "JMC_API_KEY" in prod.message and DEFAULT_REGISTRY_URL in prod.message
    assert "JMC_TEST_API_KEY" in test.message and DEFAULT_POLYGON_URL in test.message
    assert prod.data == {"target": "prod", "registry_url": DEFAULT_REGISTRY_URL}
    assert test.data == {"target": "test", "registry_url": DEFAULT_POLYGON_URL}


# --------------------------------------------------------------------------- #
# The naming rules, checked before a round trip rather than after a 422
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"namespace": "test-modules"}, True),
        ({"name": "test_panel"}, True),
        ({"namespace": "eric-mods", "name": "lactose_tolerance"}, False),
        # The hyphen/underscore split is upstream's, not a normalisation we may
        # apply: a module named `test-panel` is refused as an illegal name long
        # before anything asks whether it is test data.
        ({"namespace": "testing-lab"}, False),
    ],
)
def test_production_refuses_test_data_by_its_own_spelling(kwargs, expected):
    assert (prod_refusal("prod", **kwargs) is not None) is expected
    assert prod_refusal("test", **kwargs) is None, "the polygon is where test data belongs"


def test_an_unprefixed_polygon_rehearsal_is_advised_not_refused():
    note = polygon_naming_note("test", namespace="eric-mods", name="lactose_tolerance")
    assert note is not None and "purge-test-data" in note
    assert polygon_naming_note("test", namespace="test-mods", name="test_lactose") is None
    assert polygon_naming_note("prod", namespace="eric-mods") is None


# --------------------------------------------------------------------------- #
# The surface itself
# --------------------------------------------------------------------------- #
async def test_every_registry_tool_takes_a_target(make_client):
    """A new registry tool that forgets `target` fails here rather than in the field."""
    async with make_client() as client:
        schemas = await _schemas(client)

    registry_tools = {
        name for name in schemas if name.startswith("registry_") or name == "authenticate"
    }
    assert registry_tools == set(REGISTRY_TOOL_DEFAULTS), (
        "a registry tool was added or renamed without deciding its default instance"
    )
    for name in registry_tools:
        assert "target" in schemas[name]["properties"], f"{name} cannot be aimed at an instance"


async def test_writes_rehearse_and_catalog_reads_refuse_to_guess(make_client):
    """The asymmetry is the design. A flip here is the accident it prevents.

    Writes default to the polygon because a forgotten target there costs nothing.
    Catalog reads default to nothing at all, because the cheap-vs-irreversible
    argument does not apply to them and a wrong-instance read is what makes somebody
    think the catalog is broken. `None` in the map means "required", and it is
    asserted twice: no default in the schema, and named in `required`.
    """
    async with make_client() as client:
        schemas = await _schemas(client)

    for name, expected in REGISTRY_TOOL_DEFAULTS.items():
        schema = schemas[name]
        actual = schema["properties"]["target"].get("default")
        assert actual == expected, f"{name} defaults to {actual!r}, expected {expected!r}"
        if expected is None:
            assert "target" in schema.get("required", []), (
                f"{name} has no default target but does not require one either, so an "
                "agent can still omit it and be answered about a world it did not name"
            )


#: The catalog reads that do NOT carry a `registry_` prefix, so the map above cannot
#: see them. `compare_to_published` asks the catalog what it holds for a module and
#: is a read in every sense that matters here; it was made target-required with the
#: other four on 2026-08-21 and nothing asserted it, because the guard globs on a
#: name rather than on what the tool does.
_UNPREFIXED_CATALOG_READS = ("compare_to_published",)


async def test_the_catalog_reads_that_are_not_named_registry_anything_also_require_it(make_client):
    """A check is only as wide as the set it reads, and a prefix is not a set.

    Everything above enumerates `registry_*`. A tool that reaches the same two
    instances under a different name is invisible to it, which is how a fifth
    catalog read shipped target-required with no test saying so.
    """
    async with make_client() as client:
        schemas = await _schemas(client)

    for name in _UNPREFIXED_CATALOG_READS:
        schema = schemas[name]
        assert "target" in schema["properties"], f"{name} cannot be aimed at an instance"
        assert schema["properties"]["target"].get("default") is None, (
            f"{name} reads a catalog and must not guess which one"
        )
        assert "target" in schema.get("required", []), (
            f"{name} has no default target but does not require one either"
        )


async def test_the_delete_verbs_refuse_production_before_sending_anything(make_client):
    """Polygon-only, and the refusal is ours: a 405 from the far end is not an answer.

    Reaching the network would fail the offline ceiling instead, so a passing
    assertion here also proves nothing was sent.
    """
    async with make_client() as client:
        for tool, args in (
            (
                "registry_delete_version",
                {"namespace": "eric-mods", "name": "lactose_tolerance", "version": "1.0.0"},
            ),
            ("registry_delete_module", {"namespace": "eric-mods", "name": "lactose_tolerance"}),
        ):
            result = await client.call_tool(tool, {**args, "target": "prod"})
            payload = result.structured_content or {}
            assert payload.get("success") is False
            assert "yank" in payload.get("message", ""), (
                "the refusal has to name what production offers instead"
            )


async def test_publishing_test_data_to_production_is_refused_locally(make_client):
    async with make_client() as client:
        result = await client.call_tool(
            "registry_publish",
            {
                "namespace": "test-modules",
                "name": "lactose_tolerance",
                "version": "1.0.0",
                "spec_dir": ".",
                "target": "prod",
            },
        )
    payload = result.structured_content or {}
    assert payload.get("success") is False
    assert "test_data_on_prod" in payload.get("message", "")


async def test_the_instructions_teach_the_split(make_client):
    """The tiers doc is the agent's map; a split it does not mention is not adopted."""
    from just_module_creator.server import INSTRUCTIONS

    assert 'target="test"' in INSTRUCTIONS and 'target="prod"' in INSTRUCTIONS
    assert "polygon" in INSTRUCTIONS


# --------------------------------------------------------------------------- #
# The declared target is verified by the server (F16, closed by registry 0.13)
# --------------------------------------------------------------------------- #
def test_a_client_pins_the_mode_its_target_names():
    """Our config says which instance we *meant*; the guard checks which answered.

    `expect_mode` is why `targets.py` no longer has to end with "we deliberately
    do not verify this". It costs no request — upstream asserts it lazily, on the
    calls that spend something — so it is passed uniformly rather than per site.
    """
    settings = offline_settings()

    assert client_for("test", settings)._expect_mode == "test"
    assert client_for("prod", settings)._expect_mode == "prod"


def test_the_mode_pin_uses_the_url_for_the_same_target():
    """A pin naming one instance while the URL names the other would be worse than none."""
    settings = offline_settings()

    pairs: tuple[tuple[RegistryTarget, str], ...] = (
        ("test", DEFAULT_POLYGON_URL),
        ("prod", DEFAULT_REGISTRY_URL),
    )
    for target, url in pairs:
        client = client_for(target, settings)
        assert client.base_url == url.rstrip("/")
        assert client._expect_mode == target


def test_every_client_in_the_server_is_built_through_client_for():
    """The guard is only real if no site constructs a client of its own.

    Asserted against the source rather than by behaviour: a forgotten
    `RegistryClient(...)` somewhere would publish to an unverified instance, and
    that is exactly the failure that cannot be undone.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "src" / "just_module_creator"
    offenders = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if path.name != "targets.py" and "RegistryClient(" in path.read_text()
    }
    assert not offenders, f"construct these through targets.client_for: {sorted(offenders)}"


def test_a_token_reaches_the_client_and_absence_of_one_does_not_invent_a_header():
    settings = offline_settings()

    with_token = client_for("test", settings, token="abc")
    assert with_token._http.headers["Authorization"] == "Bearer abc"
    # No token means no header at all, not an empty bearer.
    assert "Authorization" not in client_for("test", settings)._http.headers


# --------------------------------------------------------------------------- #
# The server-side pre-flights (RM8): a verdict, and what is not one
# --------------------------------------------------------------------------- #
class _Stats:
    def model_dump(self):
        return {"variant_count": 2, "study_count": 1}


class _Validation:
    """Shaped like upstream's ValidationReport. Only the fields we project."""

    def __init__(self, **kw):
        self.valid = kw.get("valid", True)
        self.strict = kw.get("strict", True)
        self.errors = kw.get("errors", [])
        self.warnings = kw.get("warnings", [])
        self.info = kw.get("info", [])
        self.stats = _Stats()
        self.content_signature = kw.get("content_signature", "sig-abc")
        self.name_matches_path = kw.get("name_matches_path", True)
        self.published_as = kw.get("published_as", [])
        self.would_publish_module_level = kw.get("would_publish_module_level", True)


class _Check:
    def __init__(self, validation, **kw):
        self.validation = validation
        self.enrichment = kw.get("enrichment")
        self.skipped_reason = kw.get("skipped_reason")
        self.would_publish = kw.get("would_publish", False)
        self.elapsed_seconds = 1.5


class _Enrichment:
    def __init__(self, **kw):
        self.unresolved = kw.get("unresolved", [])
        self.unreachable_rsids = kw.get("unreachable_rsids", [])
        self.ref_mismatches = kw.get("ref_mismatches", [])
        self.clin_sig_conflicts = kw.get("clin_sig_conflicts", [])
        self.clin_sig_not_checked = kw.get("clin_sig_not_checked")
        self.stale_rsids = kw.get("stale_rsids", [])
        self.notes = kw.get("notes", [])
        self.identifiers = kw.get("identifiers")


def _project(report):
    from just_module_creator.tools.registry import _preflight

    return _preflight(
        report,
        spec_dir="/tmp/spec",
        namespace="test-ns",
        name="m",
        target="test",
        registry_url="https://polygon",
    )


def test_a_validate_has_no_verdict_and_that_is_the_honest_value() -> None:
    """`/validate` never runs the network tier, so it has nothing to report.

    Defaulting `verdict` to False would read as "would not publish" — a skip
    producing a negative verdict, which is the same error as a skip producing a
    positive one.
    """
    out = _project(_Validation())

    assert out.verdict is None
    assert out.module_level_clear is True
    # And the next step says what the clear answer does NOT mean.
    assert "not" in out.next_step.lower() and "publish" in out.next_step.lower()


def test_module_level_clear_is_never_worded_as_will_publish() -> None:
    """Upstream named the field carefully; the wrapper must not undo that.

    The phrase may appear, but only inside its own negation — so this checks the
    disclaimer is there, rather than banning a substring that a correct sentence
    legitimately contains.
    """
    out = _project(_Validation())

    assert "NOT" in out.next_step, "a clear module-level answer must disclaim being a green light"
    assert "registry_check" in out.next_step, "and must point at the call that does decide"


def test_a_skipped_tier_leaves_the_verdict_null_rather_than_false() -> None:
    """`skipped_reason` means the dry run never reached a verdict."""
    invalid = _Validation(
        valid=False, errors=["variants.csv: bad row"], would_publish_module_level=False
    )
    out = _project(_Check(invalid, skipped_reason="invalid_spec", would_publish=False))

    assert out.verdict is None, "a skipped tier must not report a boolean verdict"
    assert out.verdict_unavailable == "invalid_spec"
    assert any("validation error" in b for b in out.blocking)


def test_unreachable_rsids_turn_a_false_verdict_into_rerun_not_fix() -> None:
    """The S20 distinction, carried all the way to the author's next action.

    A strict publish against an unreachable Ensembl really does refuse, so the
    verdict is honestly False — but the variant may be perfectly findable, and
    telling the author to fix their spec would have them delete real rows.
    """
    enrichment = _Enrichment(unresolved=["rs6567160"], unreachable_rsids=["rs6567160"])
    out = _project(_Check(_Validation(), enrichment=enrichment, would_publish=False))

    assert out.verdict is False
    assert out.rerun_rather_than_fix == ["rs6567160"]
    # The action, not the wording: re-run comes first, and the author is not sent
    # to change the spec — which would have them delete rows that are perfectly real.
    assert "re-run" in out.next_step.lower()
    assert "before changing the spec" in out.next_step.lower()
    # And it is listed as unchecked, not as a defect in the module.
    assert any("could not be ASKED" in u for u in out.unchecked)


def test_a_check_that_could_not_run_is_listed_not_dropped() -> None:
    """`clin_sig_not_checked` never blocks, and must never vanish either."""
    enrichment = _Enrichment(clin_sig_not_checked="no ClinVar snapshot on this deployment")
    out = _project(_Check(_Validation(), enrichment=enrichment, would_publish=True))

    assert out.verdict is True
    assert any("clin_sig" in u for u in out.unchecked)
    # It is not a reason a publish would fail.
    assert not any("clin_sig" in b for b in out.blocking)


def test_identifier_findings_are_reported_as_never_moving_the_verdict() -> None:
    """A publish does not run that pass, so a finding predicts nothing about one."""

    class _Ident:
        stale_traits = ["EFO_0004340 is obsolete"]
        stale_genes = []
        gene_loci = ["rs2252481 is on chromosome 6, but HGNC puts NEGR1 on chromosome 1"]
        gene_loci_not_checked = None

    out = _project(
        _Check(_Validation(), enrichment=_Enrichment(identifiers=_Ident()), would_publish=True)
    )

    assert out.verdict is True
    joined = " ".join(out.non_blocking)
    assert "NEVER moves the verdict" in joined
    assert "different chromosome" in joined
    assert not out.blocking


def test_a_duplicate_is_blocking_and_says_a_yank_does_not_free_it() -> None:
    """The trap: a yanked match still 409s, so "yanked" must not read as "gone"."""

    class _Ref:
        namespace, name, version, yanked = "someone", "same_data", "1.0.0", True

    out = _project(_Validation(published_as=[_Ref()], would_publish_module_level=False))

    assert out.published_as[0].canonical_id == "someone/same_data@1.0.0"
    assert out.published_as[0].yanked is True
    blocking = " ".join(out.blocking)
    assert "409" in blocking
    assert "yank" in blocking.lower()


def test_no_token_is_not_a_negative_verdict() -> None:
    """The failure shape this whole model exists to avoid."""
    from just_module_creator.tools.registry import _unauthenticated_preflight

    out = _unauthenticated_preflight(
        spec_dir="/tmp/spec", namespace="ns", name="m", target="test"
    )

    assert out.verdict is None
    assert out.verdict_unavailable == "no_registry_token"
    assert not out.blocking, "nothing was checked, so nothing can be reported as blocking"
    assert "validate_module" in out.next_step


def test_no_token_leaves_the_plain_booleans_null_rather_than_false() -> None:
    """`D22`: the three-valued fields were honest and the two-valued ones beside them lied.

    Measured with no token stored, on a module that `validate_module(strict=true)`
    passes clean: `verdict` was null with `verdict_unavailable` naming the reason,
    and right beside it `valid: false` on that clean spec and
    `name_matches_path: false` for a spec dir and a `module.name` that do match.
    Both were unrun checks reading as failed ones, and `valid` is the field a
    caller branches on because it is named the same as `validate_module`'s.

    A check that could not run is not a check that passed, and it is not a check
    that failed either. `registry_url` goes the same way: no instance answered,
    so naming one would claim a request that never left.
    """
    from just_module_creator.tools.registry import _unauthenticated_preflight

    out = _unauthenticated_preflight(
        spec_dir="/tmp/spec", namespace="ns", name="m", target="test"
    )

    assert out.valid is None, "nothing was validated, so `valid` is unknown rather than false"
    assert out.name_matches_path is None, "the name was never compared against the path"
    assert out.registry_url is None, "no registry answered, so none may be named as having"
    # The fields that were already honest stay untouched.
    assert out.verdict is None
    assert out.verdict_unavailable == "no_registry_token"


def test_no_token_leaves_the_composed_gate_null_too() -> None:
    """`module_level_clear` composes three gates, and without a token none is asked.

    It stayed `false` while the two beside it became null, on the reasoning that
    nothing had established it was clear. True — and the same mistake one step along:
    `false` asserts that something module-level BLOCKS a publish, which is exactly as
    unestablished as the clear answer would be.

    `strict` is deliberately NOT part of this. It echoes the mode the call would grade
    under, which is a statement about the request rather than about a result, so it
    stays two-valued.
    """
    from just_module_creator.tools.registry import _unauthenticated_preflight

    out = _unauthenticated_preflight(
        spec_dir="/tmp/spec", namespace="ns", name="m", target="test"
    )

    assert out.module_level_clear is None
    assert out.strict is True


def test_a_card_carries_the_gene_count_that_says_its_gene_list_is_a_sample() -> None:
    """The catalog cuts `genes` to the first few and reports the real total separately.

    We read the list and dropped the total, so a module whose own description names 22
    genes showed three and looked complete — and a caller filtering the returned records
    by `genes` in memory got wrong answers with nothing saying so. Searching BY gene was
    never affected; only the projection was.

    Asserted against a payload shaped like the catalog's, so this fails if the field is
    dropped again rather than only when a live catalog is reachable.
    """
    from just_module_creator.tools.research import _module_card

    card = _module_card(
        {
            "namespace": "antonkulaga",
            "name": "aggression_anger_snps",
            "version": "2.1.0",
            "genes": ["ALCAM", "ARL17B", "ARPP21"],
            "gene_count": 22,
        }
    )

    assert card.gene_count == 22
    assert len(card.genes) < card.gene_count, "the fixture should model a truncated list"


# --------------------------------------------------------------------------- #
# A listing is narrower than the instance (F14/F20, D15)
# --------------------------------------------------------------------------- #
#: The registry leaves its test/sandbox namespaces out of an unfiltered listing on both
#: instances and counts them in `/health`, which is documented server policy. What was
#: ours was the dead end: `registry_health(target="test")` reporting a populated polygon
#: beside `registry_search(target="test")` answering `total: 0`, with no argument on the
#: tool that could ask the other question and nothing on the result saying one existed.
#: An author who rehearses a publish and searches it back concludes the publish failed.


def test_the_search_tool_can_ask_for_the_namespaces_a_listing_hides() -> None:
    """The two arguments the client has always had and this tool did not pass.

    Asserted against the installed client rather than against a remembered
    signature: `group` and `namespace` are upstream's names for upstream's facets,
    and a rename there must fail here rather than 422 in the field.
    """
    import inspect

    from just_dna_registry.client import RegistryClient

    upstream = inspect.signature(RegistryClient.list_modules).parameters
    assert {"group", "namespace"} <= set(upstream)


async def test_registry_search_exposes_group_and_namespace(make_client):
    """A filter the wire supports and the tool does not expose is unreachable."""
    async with make_client() as client:
        schemas = await _schemas(client)

    props = schemas["registry_search"]["properties"]
    for facet in ("group", "namespace"):
        assert facet in props, f"registry_search cannot ask the registry about {facet}"
        assert props[facet].get("default") is None, (
            f"{facet} must default to nothing: inferring group='test' from target='test' would "
            "hide an unprefixed polygon namespace and rebuild this defect one level up"
        )


class _StubClient:
    """Records the query it was asked for and answers with an empty page."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.seen: dict = {}

    def list_modules(self, **kwargs):
        self.seen = kwargs
        return self.payload


async def test_group_and_namespace_reach_the_registry_query(make_client, monkeypatch):
    """Passed through, under the client's own parameter names.

    `client_for` is patched where `research` bound it — the module holds its own
    reference, so patching `targets` would miss it — and the stub keeps this
    socket-free, which is what lets the ceiling be down for one call.
    """
    from just_module_creator.tools import research

    stub = _StubClient({"items": [], "total": 0, "page": 1})
    monkeypatch.setattr(research, "client_for", lambda *a, **kw: stub)

    settings = Settings(offline=False, _env_file=None, api_key=None)  # type: ignore[call-arg]
    async with make_client(settings=settings) as client:
        await client.call_tool(
            "registry_search",
            {"target": "test", "group": "test", "namespace": "test-sheep"},
        )

    assert stub.seen.get("group") == "test"
    assert stub.seen.get("namespace") == "test-sheep"


async def test_an_unfiltered_zero_says_which_namespaces_it_left_out(make_client, monkeypatch):
    """The failure an author actually hits: a rehearsal read back as `total: 0`.

    The zero is real for the listing that produced it and says nothing about the
    instance, so the result has to carry the retry rather than leaving the author
    to conclude the publish failed.
    """
    from just_module_creator.tools import research

    stub = _StubClient({"items": [], "total": 0, "page": 1})
    monkeypatch.setattr(research, "client_for", lambda *a, **kw: stub)

    settings = Settings(offline=False, _env_file=None, api_key=None)  # type: ignore[call-arg]
    async with make_client(settings=settings) as client:
        result = await client.call_tool("registry_search", {"target": "test"})

    payload = result.structured_content or {}
    assert payload["total"] == 0
    note = payload["next_step"]
    assert "test/sandbox" in note, "the zero must name what the listing left out"
    assert 'group="test"' in note, "and name the call that asks the other question"
    assert "not evidence of absence" in note


def test_a_scoped_zero_is_not_blamed_on_the_default_exclusion() -> None:
    """An explicit `namespace` pops the exclusion server-side, so that zero is measured.

    Offering the retry there would be a false explanation for a true zero, which
    is the same defect facing the other way.
    """
    from just_module_creator.tools.research import _search_next_step

    unfiltered = _search_next_step(total=0, group=None, namespace=None)
    scoped = _search_next_step(total=0, group=None, namespace="test-sheep")
    grouped = _search_next_step(total=0, group="test", namespace=None)

    assert 'group="test"' in unfiltered
    assert 'group="test"' not in scoped
    assert 'group="test"' not in grouped


def test_a_non_empty_page_still_says_it_is_not_the_whole_instance() -> None:
    """`total: 7` from a plain listing is as partial as `total: 0` is."""
    from just_module_creator.tools.research import _search_next_step

    note = _search_next_step(total=7, group=None, namespace=None)
    assert "test/sandbox" in note
    assert "no single group lists an instance whole" in note


# --------------------------------------------------------------------------- #
# Registry 0.14: an unclaimed name this surface still cannot claim
# --------------------------------------------------------------------------- #
def test_available_plus_requires_override_is_not_reported_as_a_green_light():
    """`available: true` and "go ahead" are different answers (registry 0.14).

    A `test-`prefixed namespace on production is genuinely unclaimed *and* refused
    there by default. Upstream deliberately did NOT flip `valid` to false — the
    policy moved, so the name really is claimable with the override — which leaves
    the wrapper responsible for not reading `available` alone as permission.
    Confirmed against the live instance while adopting 0.14: production answers
    `available: true, requires_allow_test_data: true` for `test-modules`.
    """
    from just_module_creator.models import NamespaceAvailability

    answer = NamespaceAvailability(
        namespace="test-modules",
        valid=True,
        available=True,
        requires_allow_test_data=True,
        warnings=["starts with 'test-', which this production instance does not accept by default"],
        message=(
            "'test-modules' is unclaimed on production, but a `test-`prefixed name is refused "
            'there by default and this server does not offer the override. Claim it on the '
            'polygon (target="test") instead.'
        ),
    )

    assert answer.available is True
    assert answer.requires_allow_test_data is True
    # The message must not read as permission, and must name the way out.
    assert "polygon" in answer.message
    assert answer.warnings, "the instance's own warning must survive"


def test_an_instance_that_does_not_report_the_override_is_null_not_false():
    """Pre-0.14 said nothing; "did not say" is not "does not require it"."""
    from just_module_creator.models import NamespaceAvailability

    answer = NamespaceAvailability(
        namespace="my-ns", valid=True, available=True, message="free"
    )

    assert answer.requires_allow_test_data is None
    assert answer.warnings == []


def test_the_prod_refusal_no_longer_claims_the_server_makes_it_impossible():
    """0.14 turned the ban into a default, so the refusal is partly ours now.

    Keeping the refusal is the decision (an agent must not wave an author's data
    onto an immutable registry); claiming the server forbids it outright would be
    a false statement about somebody else's API.
    """
    refusal = prod_refusal("prod", namespace="test-mine")

    assert refusal is not None
    assert "by default" in refusal, "the ban is a default as of 0.14, not an absolute"
    assert "does not offer it" in refusal, "and the remaining refusal is ours — say so"
    assert "polygon" in refusal


# --------------------------------------------------------------------------- #
# amend_readme: the one published-module write that is cheap (F33)
# --------------------------------------------------------------------------- #
async def test_amend_readme_refuses_a_path_masquerading_as_prose(make_client):
    """The one ambiguity worth spending two arguments on.

    Upstream's `amend_readme(readme=...)` disambiguates a path from markdown by
    TYPE, and every MCP argument arrives as a string. Collapsed into one parameter,
    `readme="spec/README.md"` would publish the path *as* the card's prose — quietly,
    and on a module whose whole problem was a card nobody could read.
    """
    from fastmcp.exceptions import ToolError

    async with make_client(offline_settings()) as client:
        args = {"namespace": "ns", "name": "m", "version": "1.0.0"}
        with pytest.raises(ToolError, match="Provide either spec_dir"):
            await client.call_tool("registry_amend_readme", args)
        with pytest.raises(ToolError, match="not both"):
            await client.call_tool(
                "registry_amend_readme",
                {**args, "spec_dir": "/tmp", "readme_text": "# hi"},
            )


async def test_amend_readme_refuses_to_blank_a_card(make_client, tmp_path):
    """Sending empty prose would replace a readme rather than repair one.

    Last-publish-wins is the registry's rule for the field, so an empty body is
    accepted and destroys what was there. The tool is for fixing a blank card, so
    making one is the failure mode to close.
    """
    from fastmcp.exceptions import ToolError

    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError, match="blank the card"):
            await client.call_tool(
                "registry_amend_readme",
                {"namespace": "ns", "name": "m", "version": "1.0.0", "readme_text": "   \n"},
            )


async def test_amend_readme_names_the_exact_filename_it_reads(make_client, tmp_path):
    """A spec dir with no README.md must say which name the registry reads.

    `MODULE.md` is renamed on upload and anything else is carried-but-never-read, so
    "no readme found" without the exact name is the dead end this message removes.
    """
    from fastmcp.exceptions import ToolError

    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "MODULE.md").write_text("# the old name")

    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError, match="README.md"):
            await client.call_tool(
                "registry_amend_readme",
                {
                    "namespace": "ns",
                    "name": "m",
                    "version": "1.0.0",
                    "spec_dir": str(spec),
                },
            )


# --------------------------------------------------------------------------- #
# Yank (RM21)
# --------------------------------------------------------------------------- #
async def test_yank_is_gated_and_reversible_and_says_it_repairs_nothing(make_client):
    """The three properties that make yank safe to hand an agent.

    It is a registry write, so it needs a token like every other one. It is
    listed in both directions, because a yank nobody can reverse is a worse
    first move than no yank at all. And its own description must not let an
    agent report it as a fix: the mistake is still published, still fetchable,
    and the corrected module is a separate publish that has not happened yet.
    """
    async with make_client(offline_settings()) as client:
        tools = {t.name: t for t in await client.list_tools()}

        assert {"registry_yank", "registry_unyank"} <= set(tools)
        assert {"registry_yank", "registry_unyank"} <= set(GATED_TOOLS)

        # Without a token it reports rather than raises — an agent that has just
        # found a grave error must not meet a traceback.
        result = await client.call_tool(
            "registry_yank", {"namespace": "ns", "name": "m", "version": "1.0.0"}
        )
        assert result.data.success is False
        assert "registry token" in result.data.message

        described = tools["registry_yank"].description or ""
        assert "not a repair" in described.lower()
        # The content claim is the fact an author is most likely to assume wrong:
        # a yank looks like an undo, and the authored data stays claimed.
        assert "content claim" in described


async def test_yank_defaults_to_the_polygon_like_every_other_write(make_client):
    """Production is where a yank matters and still not where it points by default.

    An unaimed yank that silently delisted a production version would be the
    same class of mistake the tool exists to recover from.
    """
    async with make_client(offline_settings()) as client:
        schemas = {t.name: t.inputSchema for t in await client.list_tools()}
        for name in ("registry_yank", "registry_unyank"):
            assert schemas[name]["properties"]["target"]["default"] == "test"
