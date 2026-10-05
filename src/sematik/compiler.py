"""Semantic compiler — approved Mapping → deterministic executable plan (§19).

A transformation plan is deterministic data; the executor applies it to rows of
a source record. Generated plans carry their mapping digest for traceability
and reproduce under identical inputs (§22/§69).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .mapping import Mapping
from .model import Assertion, Confidence, DerivationStatus, Provenance


class CompilationError(Exception):
    pass


class ConversionUngecognizable(Exception):
    """A row whose values do not fit the compiled plan — must surface
    (spec §68). It is never silently coerced."""

    def __init__(self, record_id: str, reason: str):
        super().__init__(f"{record_id}: {reason}")
        self.record_id = record_id
        self.reason = reason


@dataclass
class PlanStep:
    op: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationPlan:
    mapping_id: str
    mapping_digest: str
    target_artifact: str
    steps: list[PlanStep] = field(default_factory=list)

    def execute(self, row: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for step in self.steps:
            out = _apply(step, row, out)
        return out


def _apply(step: PlanStep, row: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    if step.op == "copy":
        src, dst = step.args["from"], step.args["to"]
        if src not in row:
            raise ConversionUngecognizable(str(row.get("_id", "?")), f"missing source field {src}")
        out[dst] = row[src]
        return out
    if step.op == "rename":
        return _apply(PlanStep("copy", step.args), row, out)
    if step.op == "derive_sum":
        total = 0
        for f in step.args["parts"]:
            v = row.get(f)
            if v is None:
                raise ConversionUngecognizable(str(row.get("_id", "?")), f"missing component {f}")
            total += float(v)
        out[step.args["to"]] = total
        return out
    if step.op == "code_translate":
        raw = row.get(step.args["from"])
        mapping = step.args["table"]
        if raw not in mapping:
            raise ConversionUngecognizable(str(row.get("_id", "?")),
                                           f"value {raw!r} not in code table for {step.args['from']}")
        out[step.args["to"]] = mapping[raw]
        return out
    if step.op == "assert_not_null":
        if row.get(step.args["field"]) is None:
            raise ConversionUngecognizable(str(row.get("_id", "?")), f"{step.args['field']} is null")
        return out
    raise CompilationError(f"unknown op {step.op}")


def compile_mapping(mapping: Mapping, steps: list[PlanStep]) -> TransformationPlan:
    if not mapping.approved():
        raise CompilationError("mapping must be approved before compilation")
    if not steps:
        raise CompilationError("a transformation plan needs at least one step")
    return TransformationPlan(
        mapping_id=mapping.id,
        mapping_digest=mapping.digest(),
        target_artifact=mapping.target_artifact,
        steps=steps,
    )


def assertion_from_plan_output(plan: TransformationPlan, target: dict[str, Any],
                               provenance: Provenance, mapping: Mapping) -> Assertion:
    """Wrap a converted target value as an assertion with lineage."""
    return Assertion(
        concept=mapping.canonical_concept,
        value=target.get(plan.target_artifact) or next(iter(target.values()), None),
        derivation=DerivationStatus.DERIVED_VALUE,
        provenance=provenance,
        confidence=mapping.confidence,
        transformation_history=(plan.mapping_digest,),
        validation_state="pending",
    )
