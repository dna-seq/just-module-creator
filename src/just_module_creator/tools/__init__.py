"""Tool registration modules, grouped by what they do.

One surface: every module here is registered on every start. There is no mode
axis — ``JMC_MODE`` and ``--mode`` are gone, and the only thing that narrows what
a session sees is ``JMC_TOOL_SEARCH`` (discovery) or a missing token (auth).

- ``authoring``  — the offline loop: schema answers, scaffold, lint, validate, compile.
- ``checks``     — ``check_identifiers``: asks a source and records that it was asked.
- ``research``   — read-only lookups: variants, citations, literature, papers.
- ``passes``     — the tools that fetch and then write into a spec directory.
- ``refresh``    — re-derive one sidecar against its source, keeping your own rows.
- ``provenance`` — recording an override, and reading the queue back.
- ``comparison`` — two local spec directories, offline, at three grains.
- ``advanced``   — the citation graph and the artifact reads.
- ``registry``   — token-gated registry writes (tag ``registry_write``).
"""
