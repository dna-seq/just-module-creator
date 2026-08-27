"""OPTIONAL — collapse the tool listing into an on-demand search interface.

Off by default. With ``JMC_TOOL_SEARCH=regex|bm25`` (or ``--tool-search``) the
server stops listing its tools and lists two synthetic ones instead —
``search_tools`` and ``call_tool`` — so a client discovers the rest by querying.

**This is the lever the mode axis is not.** The tier decided what *existed* at
startup, for everybody, and it kept costing sessions the tools they needed
(``docs/previous_issues.md``, ``F47``). Search changes only how the surface is
*presented*, per client, and nothing becomes unreachable: an unlisted tool is
still callable by name. That is the difference worth keeping straight before
anyone reaches for this to "trim the surface" again.

Which strategy:

* ``regex`` — case-insensitive substring match over name, description and
  parameter docs. Deterministic, no index, and blunt: a search for "publish"
  also matches every tool whose description mentions publishing.
* ``bm25``  — Okapi BM25 relevance ranking over the same text, with a lazily
  built in-memory index. Better for a natural-language query.

Worth knowing before turning it on:

* A client that calls an unlisted tool by name never received its schema, so
  FastMCP's own client degrades ``result.data`` from a typed model to a plain
  dict. Every tool here returns a pydantic model whose field descriptions are
  half of what it teaches, so prefer ``call_tool`` if you want them.
* It composes with auth: search sees what the session may see, so with
  ``JMC_HIDE_GATED_UNTIL_AUTH`` the registry writes are undiscoverable until
  that session authenticates.
* Only tools are replaced. The ``resource://just-dna/tables`` resource and the
  ``create_module`` prompt list as usual.
* This surface runs to dozens of tools, which is the size at which search starts
  earning its keep rather than costing a round trip.
"""

from __future__ import annotations

from fastmcp import FastMCP

from just_module_creator.logging_setup import get_logger
from just_module_creator.settings import Settings

log = get_logger()

#: Pinned into the listing even when search is on, because they are the way in.
#: ``registry_register`` mints the token every gated tool needs and
#: ``authenticate`` stores one you already hold — a client that has to *search*
#: for the route to a credential is the dead end `F12` closed, arriving through a
#: different door. ``toolbox`` is here for the same reason one layer up: it is the
#: roster of everything a layered server is holding back, and a roster nobody can
#: find is not a roster. All three are cheap and none reads a corpus.
ALWAYS_VISIBLE = ["registry_register", "authenticate", "toolbox"]


def apply_tool_search(mcp: FastMCP, settings: Settings) -> None:
    """Add the configured search transform. A no-op when ``tool_search`` is off.

    Call this LAST in ``build_server``: a search transform indexes whatever tools
    are registered by the time it runs.
    """
    if settings.tool_search == "off":
        return

    from fastmcp.server.transforms.search import (
        BM25SearchTransform,
        RegexSearchTransform,
    )

    cls = BM25SearchTransform if settings.tool_search == "bm25" else RegexSearchTransform
    mcp.add_transform(
        cls(
            max_results=settings.tool_search_max_results,
            always_visible=list(ALWAYS_VISIBLE),
        )
    )
    log.info(
        "Tool search enabled (%s, max_results=%d)",
        settings.tool_search,
        settings.tool_search_max_results,
    )
