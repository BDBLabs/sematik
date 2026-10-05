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


def reconcile_records(rows: Iterable[dict[str, Any]],
                      outputs: Iterable[dict[str, Any]], *,
                      source_key: str, target_key: str,
                      numeric_pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Record-level reconciliation (§30): for each reconciled row, verify the
    source's numeric derivation of the canonical target still holds — a system
    that balances in aggregate but attaches values to the wrong entities fails
    this check (spec §30)."""
    src_by_key = {str(r.get(source_key)): r for r in rows}
    mismatches: list[dict[str, Any]] = []
    checked = 0
    for out in outputs:
        tk = str(out.get(target_key))
        src = src_by_key.get(tk)
        if src is None:
            continue
        checked += 1
        for src_total_field, tgt_field in numeric_pairs:
            expected = None
            src_parts = src.get(src_total_field)
            if isinstance(src_parts, list):
                expected = sum(float(p) for p in src_parts)
            elif isinstance(src_parts, (int, float)):
                expected = float(src_parts)
            if expected is not None and tgt_field in out:
                if abs(float(out[tgt_field]) - expected) > 1e-6:
                    mismatches.append({"key": tk, "field": tgt_field,
                                       "expected": expected, "got": out[tgt_field]})
    return {"checked": checked, "mismatches": mismatches,
            "balanced": not mismatches and checked > 0}


def semantic_reconcile(assertions: Iterable,
                       invariants: Iterable[tuple[str, Callable]]) -> dict[str, Any]:
    checked, failures = 0, []
    for desc, inv in invariants:
        checked += 1
        if not inv(assertions):
            failures.append(desc)
    return {"invariants_checked": checked, "failures": failures}
