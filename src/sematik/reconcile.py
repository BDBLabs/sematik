"""Reconciliation — population and record-level balance (spec §30)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable


def population_reconcile(source_rows: Iterable[dict[str, Any]],
                         outputs: Iterable[dict[str, Any]],
                         *, source_key: str, target_key: str) -> dict[str, Any]:
    src = Counter(str(r.get(source_key)) for r in source_rows)
    tgt = Counter(str(r.get(target_key)) for r in outputs)
    source_ids = set(src)
    target_ids = set(tgt)
    return {
        "source_records": sum(src.values()),
        "target_records": sum(tgt.values()),
        "missing_in_target": sorted(source_ids - target_ids),
        "extra_in_target": sorted(target_ids - source_ids),
        "balanced": source_ids == target_ids and sum(src.values()) == sum(tgt.values()),
    }


def semantic_reconcile(assertions: Iterable,
                       invariants: Iterable[tuple[str, Callable]]) -> dict[str, Any]:
    checked, failures = 0, []
    for desc, inv in invariants:
        checked += 1
        if not inv(assertions):
            failures.append(desc)
    return {"invariants_checked": checked, "failures": failures}
