"""Golden Records — regression anchors whose meaning must survive any
mapping change (spec §35/§61)."""

from __future__ import annotations

from typing import Any, Callable

from .compiler import TransformationPlan


def run_golden_records(plan: TransformationPlan, golden: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for g in golden:
        row = g["input"]
        try:
            got = plan.execute(row)
        except Exception as e:
            failures.append({"name": g.get("name", "?"), "error": str(e)})
            continue
        if got != g["expected"]:
            failures.append({"name": g.get("name", "?"),
                             "expected": g["expected"], "got": got})
    return {"checked": len(golden), "failures": failures, "ok": not failures}
