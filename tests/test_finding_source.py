"""F120: `LintFinding.source` says which layer computed a finding, and nothing defaults it.

The field once defaulted to `upstream`, so every finding the literature tools computed
(`discovery.py`: outage notices, the PubMed join, "nothing was retrieved") reached the agent
labelled as the compiler's. The two producers are pinned here: a finding carried across from
upstream says `upstream`, one this layer computes says `just-module-creator`, and a finding
that says neither is refused at construction.
"""

from __future__ import annotations

import pytest
from just_dna_compiler.hints import Finding
from pydantic import ValidationError

from just_module_creator.models import OURS, UPSTREAM, LintFinding
from just_module_creator.tools._shared import to_findings


def test_a_finding_that_names_no_layer_is_refused() -> None:
    with pytest.raises(ValidationError, match="source"):
        LintFinding(level="info", message="no layer named")  # type: ignore[call-arg]


def test_a_finding_carried_from_upstream_says_upstream() -> None:
    upstream = Finding(0, "unresolved", "error", "Input should be a valid boolean", 3)
    (carried,) = to_findings([upstream])
    assert carried.source == UPSTREAM


def test_the_two_labels_differ() -> None:
    assert OURS != UPSTREAM and OURS == "just-module-creator"
