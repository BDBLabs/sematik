"""Reconciliation — population and record-level balance (spec §30)."""

from __future__ import annotations

import math
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


def _finite_number(value: Any) -> float | None:
    """Return a finite float for real numeric input, else None.

    Bools, NaN, infinities, and non-numeric values are not valid amounts —
    they must surface as mismatches (spec §68), never pass silently.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    return None


def _check_pair(tk: str, src_total_field: str, tgt_field: str,
                src: dict[str, Any], out: dict[str, Any]) -> dict[str, Any] | None:
    """Return a mismatch record for one numeric pair, or None if it holds."""
    if tgt_field not in out:
        return {"key": tk, "field": tgt_field, "kind": "missing_target",
                "reason": f"target field {tgt_field!r} absent"}
    got = _finite_number(out[tgt_field])
    if got is None:
        return {"key": tk, "field": tgt_field, "kind": "invalid_target",
                "reason": f"target value {out[tgt_field]!r} is not a finite number",
                "got": out[tgt_field]}
    src_parts = src.get(src_total_field)
    if isinstance(src_parts, list):
        try:
            expected = sum(float(p) for p in src_parts if not isinstance(p, bool))
        except (TypeError, ValueError):
            expected = None
        if expected is None or not math.isfinite(expected):
            expected = None
    elif isinstance(src_parts, (int, float)) and not isinstance(src_parts, bool):
        expected = float(src_parts) if math.isfinite(float(src_parts)) else None
    else:
        expected = None
    if expected is None:
        return {"key": tk, "field": tgt_field, "kind": "unsupported_source",
                "reason": f"source field {src_total_field!r} holds {src_parts!r}, "
                          "not numeric input"}
    if abs(got - expected) > 1e-6:
        return {"key": tk, "field": tgt_field,
                "expected": expected, "got": out[tgt_field]}
    return None


def reconcile_records(rows: Iterable[dict[str, Any]],
                      outputs: Iterable[dict[str, Any]], *,
                      source_key: str, target_key: str,
                      numeric_pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Record-level reconciliation (§30): for each reconciled row, verify the
    source's numeric derivation of the canonical target still holds — a system
    that balances in aggregate but attaches values to the wrong entities fails
    this check (spec §30).

    Fail-closed: absent/non-finite/non-numeric target values, missing or
    unsupported source values, outputs with no source row, and duplicated
    keys are all reported explicitly. ``balanced`` requires at least one
    fully verified row and zero findings of any kind.
    """
    src_list = list(rows)
    out_list = list(outputs)
    src_keys = [str(r.get(source_key)) for r in src_list]
    out_keys = [str(o.get(target_key)) for o in out_list]
    src_by_key = dict(zip(src_keys, src_list, strict=True))
    duplicates = sorted({k for k, c in Counter(src_keys).items() if c > 1}
                        | {k for k, c in Counter(out_keys).items() if c > 1})
    mismatches: list[dict[str, Any]] = []
    unmatched: list[str] = []
    checked = 0
    for out, tk in zip(out_list, out_keys, strict=True):
        src = src_by_key.get(tk)
        if src is None:
            unmatched.append(tk)
            continue
        checked += 1
        for src_total_field, tgt_field in numeric_pairs:
            bad = _check_pair(tk, src_total_field, tgt_field, src, out)
            if bad is not None:
                mismatches.append(bad)
    return {"checked": checked, "mismatches": mismatches,
            "unmatched": unmatched, "duplicates": duplicates,
            "balanced": not mismatches and not unmatched
            and not duplicates and checked > 0}


def semantic_reconcile(assertions: Iterable,
                       invariants: Iterable[tuple[str, Callable]]) -> dict[str, Any]:
    checked, failures = 0, []
    for desc, inv in invariants:
        checked += 1
        if not inv(assertions):
            failures.append(desc)
    return {"invariants_checked": checked, "failures": failures}
