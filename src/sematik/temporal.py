"""Temporal context — distinct dimensions are detectable, not flattened (§9).

This is a structural layer: it characterizes assertions by which temporal
dimensions are present and flags uncertainty. Full reconstruction (§10) is
future work.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

DIMENSION_FIELDS = [
    "effective_date", "transaction_date", "system_recorded_date",
    "observation_date", "filing_date", "period",
]


def temporal_coverage(assertions: Iterable) -> dict[str, int]:
    counts: Counter = Counter()
    for a in assertions:
        for dim in DIMENSION_FIELDS:
            v = getattr(a.temporal, dim, None)
            if v not in (None, ""):
                counts[dim] += 1
    return dict(counts)


def temporal_uncertainty_flags(assertions: Iterable) -> list[dict]:
    """Flag assertions carrying <=1 known temporal dimension: their temporal
    semantics are effectively unknown and must surface in the run report."""
    flags = []
    for a in assertions:
        known = a.temporal.known_dimensions()
        if len(known) <= 1:
            flags.append({"assertion": a.id, "concept": a.concept,
                          "known_dimensions": known,
                          "reason": "<=1 temporal dimension recorded"})
    return flags
