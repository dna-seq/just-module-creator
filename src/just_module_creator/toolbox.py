"""OPTIONAL — a two-layer tool surface: a working spine, and the rest on request.

Off by default (``JMC_TOOLBOX=flat``). With ``JMC_TOOLBOX=layered`` the server
lists only the **core** group and hides the other nine behind ``toolbox``, which
names every one of them and reveals a group to the calling session on request.

**This is not the mode axis coming back, and the difference is measured rather
than asserted.** That axis decided at server start, for every session, that a
tool did not exist; nothing named the missing tools, and a session that needed
one had to be restarted with a different environment. Four times a surface
taught a step it could not run (``docs/previous_issues.md``, ``F47``). Here the
roster is always readable, the reveal is one call, and it is scoped to the
session that asked — so the worst case is a round trip, not a dead end.

**The numbers this exists for**, measured at 0.23.0 over the serialized
``tools/list`` payload (o200k tokenizer, so ±a few percent for Claude's):

* the flat listing is **58,586 tokens** — 29.3% of a 200k window before a single
  row of anyone's module is read;
* layered it is **17,759** — 8.9% of that window, a saving of **40,827 tokens
  (70%)**;
* with ``tool_search`` on top, **2,507** (95.7% saved), at the price of a search
  before the first call;
* one tool, ``refresh_sidecar``, is **5,841** — a tenth of the whole listing,
  which says the second lever is prose rather than grouping. That lever was
  pulled in 0.23.0 and it is not finished.

Against the surface as it stood at 0.22.0, before the docstring pass: the whole
listing was 61,458 tokens and the old ``extended`` tier hid 6 tools worth
**7,614** of it — a 14.4% saving, which is why that tier was never worth what it
cost, and the comparison the rest of this file is arguing with.

**The host has to honour ``notifications/tools/list_changed``** for a reveal to
land mid-session; ``ctx.enable_components`` sends it. That is why the default is
``flat``: on a client that ignores the notification, a revealed group is only
visible after a reconnect, which is the restart problem wearing a new hat. Flip
this on where you have checked, or where the session is long enough that one
reconnect is cheaper than 40k tokens.

Composes with ``tool_search``: search sees what the session may see, so a hidden
group is not searchable until it is revealed.

**It does not route around ``JMC_HIDE_GATED_UNTIL_AUTH``, and that took a test to
settle rather than an assumption.** Session rules override global ones, so a
reveal by *name* does beat that flag's disable by *tag* — measured, not guessed —
which would have let any session list the publish route by asking for it, and an
operator who set the flag set it precisely so that could not happen. So
``toolbox`` checks: with the flag on and no token resolvable for this session,
the ``publish`` group is held back and the answer says `authenticate` is the way
in. Visibility was never the gate either way — the per-call token check is
untouched, and a listed registry tool still refuses without a token.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from just_module_creator.auth import resolve_api_key
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import ToolboxGroup, ToolboxResult
from just_module_creator.settings import Settings

log = get_logger()


@dataclass(frozen=True)
class Group:
    """One layer-2 group: what it is for, which tools it holds, what listing it costs."""

    name: str
    summary: str
    tools: tuple[str, ...]
    #: Roughly what listing this group would add to a client's context: the
    #: serialized ``tools/list`` entries, characters ÷ 4. Measured 2026-08-27 and
    #: **written down rather than computed**, because a hidden tool is invisible
    #: to ``get_tool``/``list_tools`` — visibility filtering applies to us too, so
    #: a layered server cannot measure what it is holding back. That makes this a
    #: fact we cannot generate, so it is guarded by a test instead:
    #: ``test_the_group_sizes_are_still_true`` rebuilds a FLAT server, measures,
    #: and fails when any entry drifts more than 20%. Against a real tokenizer the
    #: ÷4 estimate reads about 8% high on this surface.
    approx_tokens: int


#: The spine. Everything ``server.INSTRUCTIONS`` teaches is here, plus the two
#: cells rule 2 and rule 5 send an author to and the route to a credential —
#: `test_the_core_group_covers_the_taught_workflow` derives that first half from
#: the instruction text rather than trusting this list.
CORE = (
    "list_tables",
    "describe_table",
    "table_requirements",
    "describe_machine_table",
    "get_template",
    "scaffold_module",
    "lint_rows",
    "validate_module",
    "compile_module",
    "draft_from_clinvar",
    "enrich_module",
    "literature_search",
    "lookup_citation",
    "lookup_variant",
    "record_override",
    "registry_register",
    "authenticate",
)

#: Layer 2, granular on purpose: a session that needs to read one paper should
#: not have to reveal the registry to do it. Nine groups rather than the three a
#: coarse split suggests, because the coarse split is what made the old tier's
#: line arbitrary — "extended" bundled a PGx drafter with a citation graph.
GROUPS: tuple[Group, ...] = (
    Group(
        "evidence",
        "Read a paper: a legal copy, its full text, who cited it, and the "
        "supplementary tables its per-variant numbers are actually in.",
        (
            "lookup_open_access",
            "fetch_fulltext",
            "paper_citations",
            "list_supplementary",
            "fetch_supplementary",
            "describe_supplementary",
        ),
        6374,
    ),
    Group(
        "identifiers",
        "Is this gene symbol / ontology CURIE current, and does it agree with the row.",
        ("check_identifiers", "lookup_identifier"),
        2569,
    ),
    Group(
        "pgx",
        "Draft the pharmacogenomics tables from CPIC or a ClinPGx snapshot.",
        ("draft_from_cpic", "draft_from_clinpgx"),
        2291,
    ),
    Group(
        "passes",
        "Fill or re-derive the machine-written sidecars. A corpus sizes three of these.",
        (
            "enrich_facts",
            "enrich_literature_pass",
            "enrich_gwas_effects",
            "refresh_sidecar",
        ),
        10275,
    ),
    Group(
        "review",
        "Read a module back: the decision list, the override queue, the logs, the study facts.",
        ("audit_module", "review_queue", "review_logs", "study_facts"),
        5040,
    ),
    Group(
        "integrity",
        "Did anything move: two spec directories, a signature, an artifact, a reversal.",
        (
            "compare_modules",
            "compare_to_published",
            "module_signature",
            "verify_artifact",
            "reverse_module",
        ),
        4677,
    ),
    Group(
        "catalog",
        "Read the registry: search it, read a module, download one, check a name is free.",
        (
            "registry_search",
            "registry_get_module",
            "registry_health",
            "registry_is_published",
            "registry_namespace_available",
            "registry_download",
        ),
        4532,
    ),
    Group(
        "publish",
        "Write to the registry. Every one needs a token; a prod publish is immutable.",
        (
            "registry_whoami",
            "registry_validate",
            "registry_check",
            "registry_publish",
            "registry_amend_readme",
            "registry_claim_namespace",
            "registry_yank",
            "registry_unyank",
            "registry_delete_version",
            "registry_delete_module",
        ),
        7486,
    ),
    Group(
        "closing",
        "Finish and describe: close the module, the spec file's own schema, the whole DSL.",
        ("close_module", "describe_spec_file", "authoring_reference"),
        2718,
    ),
)

BY_NAME = {group.name: group for group in GROUPS}

#: Every tool that is not listed until a session asks for it.
HIDDEN = tuple(name for group in GROUPS for name in group.tools)


def hide_layer_two(mcp: FastMCP) -> None:
    """Hide every non-core tool at startup. Server-global, which is correct HERE.

    ``mcp.disable`` is server-global and must never be driven by one client's
    request; as the *starting* state it is exactly right. The per-session half is
    ``ctx.enable_components`` inside ``toolbox``.
    """
    mcp.disable(names=set(HIDDEN))


def register_toolbox(mcp: FastMCP, settings: Settings) -> None:
    """Register ``toolbox``: the roster of layer 2, and the way to reveal it."""

    layered = settings.toolbox == "layered"
    groups_line = ", ".join(g.name for g in GROUPS)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="What else is in the toolbox, and reveal it",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
        )
    )
    async def toolbox(ctx: Context, groups: list[str] | None = None) -> ToolboxResult:
        """What this server can do beyond the tools you can see, and how to get it.

        Call it with no arguments for the roster: every group, what it is for, the tools
        in it, and roughly what listing it would cost. Call it with `groups` to reveal
        those groups **to this session** — they appear in your tool list and stay. The
        groups are `evidence` (read a paper), `identifiers` (is this symbol or CURIE
        current), `pgx` (draft the pharmacogenomics tables), `passes` (fill or re-derive
        the machine-written sidecars), `review` (read a module back), `integrity` (did
        anything move), `catalog` (read the registry), `publish` (write to it, token
        needed), `closing` (finish and describe); `groups=["all"]` reveals everything.
        Nothing here is unreachable and nothing is switched off — in the default `flat`
        configuration every tool is already listed and a reveal is a no-op that says so,
        while `JMC_TOOLBOX=layered` holds the non-core groups here and is measured at
        40,800 tokens of context. Two limits: revealing `publish` needs a token first
        where the server hides the registry writes until a session authenticates, and if
        a skill names a tool you cannot see, **call this** rather than concluding the
        capability does not exist or reaching for a shell recipe, which loses whatever
        the tool does beyond fetching.
        """
        wanted = [g.strip() for g in (groups or []) if g.strip()]
        unknown = [g for g in wanted if g != "all" and g not in BY_NAME]
        if unknown:
            return ToolboxResult(
                layered=layered,
                revealed=[],
                message=(
                    f"Unknown group(s): {', '.join(unknown)}. The groups are {groups_line}, "
                    "or 'all'. Call with no arguments for the roster."
                ),
                groups=[],
            )

        chosen = list(GROUPS) if "all" in wanted else [BY_NAME[g] for g in wanted]

        # The operator's policy outranks a reveal: see the module docstring.
        withheld = ""
        if settings.hide_gated_until_auth and any(g.name == "publish" for g in chosen):
            has_token = False
            for target in ("test", "prod"):
                if await resolve_api_key(ctx, settings, target):
                    has_token = True
                    break
            if not has_token:
                chosen = [g for g in chosen if g.name != "publish"]
                withheld = (
                    " The `publish` group was NOT revealed: this server hides the registry "
                    "writes until a session authenticates (JMC_HIDE_GATED_UNTIL_AUTH), and "
                    "revealing them here would route around that. Call "
                    "`authenticate(token, target=...)` — or `registry_register` if you have no "
                    "account — and they appear."
                )

        roster = [
            ToolboxGroup(
                name=group.name,
                summary=group.summary,
                tools=list(group.tools),
                tool_count=len(group.tools),
                approx_tokens=group.approx_tokens,
            )
            for group in GROUPS
        ]

        # `wanted`, not `chosen`: a request whose only group was withheld above is
        # not a request for the roster, and answering it with the roster would drop
        # the one sentence saying why nothing happened.
        if not wanted:
            total = sum(g.approx_tokens for g in roster)
            return ToolboxResult(
                layered=layered,
                revealed=[],
                groups=roster,
                message=(
                    f"{len(HIDDEN)} tools in {len(GROUPS)} groups, about {total} tokens if you "
                    "listed them all. "
                    + (
                        "They are hidden until you ask: call `toolbox(groups=[...])` with the "
                        "ones you need."
                        if layered
                        else "This server is in `flat` mode, so they are already in your tool "
                        "list — nothing to reveal."
                    )
                ),
            )

        if not layered:
            return ToolboxResult(
                layered=False,
                revealed=[g.name for g in chosen],
                groups=roster,
                message=(
                    "Nothing was hidden: this server lists every tool already "
                    "(`JMC_TOOLBOX=flat`). The named tools are in your list now and were "
                    "before this call." + withheld
                ),
            )

        names = {name for group in chosen for name in group.tools}
        if not names:
            return ToolboxResult(
                layered=True,
                revealed=[],
                groups=roster,
                message="Nothing was revealed." + (withheld or " No group was named."),
            )
        await ctx.enable_components(names=names)
        log.info(
            "Session %s revealed %s (%d tools)",
            ctx.session_id,
            ",".join(g.name for g in chosen),
            len(names),
        )
        still_hidden = [g.name for g in GROUPS if g not in chosen]
        return ToolboxResult(
            layered=True,
            revealed=[g.name for g in chosen],
            groups=roster,
            message=(
                f"Revealed {len(names)} tools to THIS session: {', '.join(sorted(names))}. "
                + (
                    f"Still held back: {', '.join(still_hidden)} — call again for those."
                    if still_hidden
                    else "Every group is now listed."
                )
                + withheld
                + " If your client does not refresh its tool list on "
                "notifications/tools/list_changed, reconnect once and they will be there."
            ),
        )
