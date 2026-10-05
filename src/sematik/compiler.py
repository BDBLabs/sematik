"""Semantic compiler — approved Mapping → deterministic executable plan (§19).

A transformation plan is deterministic, *immutable* data; the executor applies
it to rows of a source record. A plan carries its mapping digest and the
approval it was compiled under, and has a content digest that changes if any
step changes, so a manifest can identify exactly what executed (§22/§69).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from .mapping import Mapping
from .model import Assertion, DerivationStatus, Provenance


class CompilationError(Exception):
    pass


class ConversionUngecognizable(Exception):
    """A row whose values do not fit the compiled plan — must surface
    (spec §68). It is never silently coerced."""

    def __init__(self, record_id: str, reason: str):
        super().__init__(f"{record_id}: {reason}")
        self.record_id = record_id
        self.reason = reason


class LineageError(ValueError):
    """Conversion output cannot be bound into a lineage assertion."""


def _freeze(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        value = dict(value)
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _canon(value: Any) -> Any:
    """Order-independent, JSON-safe form used only for hashing."""
    if isinstance(value, (dict, MappingProxyType)):
        return {repr(k): _canon(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canon(v) for v in value]
    return value


@dataclass(frozen=True)
class PlanStep:
    op: str
    args: Any = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Deep-copy into read-only structures: later mutation of the caller's
        # dict can neither alter the plan nor evade the plan digest.
        object.__setattr__(self, "args", _freeze(dict(self.args)))


_REQUIRED_ARGS = {
    "copy": ("from", "to"),
    "rename": ("from", "to"),
    "derive_sum": ("parts", "to"),
    "code_translate": ("from", "to", "table"),
    "assert_not_null": ("field",),
}


def _validate_step(step: PlanStep) -> None:
    required = _REQUIRED_ARGS.get(step.op)
    if required is None:
        raise CompilationError(f"unknown op {step.op!r}")
    missing = [a for a in required if a not in step.args]
    if missing:
        raise CompilationError(f"op {step.op!r} missing required args {missing}")
    if step.op == "derive_sum" and (not isinstance(step.args["parts"], tuple)
                                    or not step.args["parts"]):
        raise CompilationError("derive_sum 'parts' must be a non-empty list")
    if step.op == "code_translate" and (not isinstance(step.args["table"], MappingProxyType)
                                        or not step.args["table"]):
        raise CompilationError("code_translate 'table' must be a non-empty mapping")


@dataclass(frozen=True)
class TransformationPlan:
    mapping_id: str
    mapping_digest: str
    target_artifact: str
    steps: tuple = ()
    approved_by: str = ""
    approval_ref: str = ""
    mapping_version: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))

    def digest(self) -> str:
        """Content digest over everything that determines behavior and the
        approval the plan was compiled under (full SHA-256)."""
        payload = json.dumps({
            "mapping_id": self.mapping_id, "mapping_digest": self.mapping_digest,
            "target": self.target_artifact,
            "steps": [{"op": s.op, "args": _canon(s.args)} for s in self.steps],
            "approved_by": self.approved_by, "approval_ref": self.approval_ref,
            "mapping_version": self.mapping_version,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def bound_to(self, mapping: Mapping) -> bool:
        """True only if the mapping is unchanged, and still approved by the
        same approver, reference and version, since this plan was compiled."""
        return (self.mapping_id == mapping.id
                and self.mapping_digest == mapping.digest()
                and self.approved_by == mapping.approved_by
                and self.approval_ref == mapping.approval_ref
                and self.mapping_version == mapping.version)

    def execute(self, row: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for step in self.steps:
            out = _apply(step, row, out)
        return out


def _rid(row: dict[str, Any]) -> str:
    return str(row.get("_id", "?"))


def _number(value: Any, rid: str, name: str) -> float:
    if isinstance(value, bool):
        raise ConversionUngecognizable(rid, f"component {name} is boolean, not numeric")
    if isinstance(value, (int, float, Decimal)):
        raw = value
    elif isinstance(value, str):
        raw = value.strip()
    else:
        raise ConversionUngecognizable(
            rid, f"component {name} has unsupported type {type(value).__name__}")
    try:
        number = float(raw)
    except (ValueError, OverflowError, TypeError):
        raise ConversionUngecognizable(rid, f"component {name} is not numeric") from None
    if not math.isfinite(number):
        raise ConversionUngecognizable(rid, f"component {name} is not finite")
    return number


def _apply(step: PlanStep, row: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    if step.op == "copy":
        src, dst = step.args["from"], step.args["to"]
        if src not in row:
            raise ConversionUngecognizable(_rid(row), f"missing source field {src}")
        out[dst] = row[src]
        return out
    if step.op == "rename":
        return _apply(PlanStep("copy", step.args), row, out)
    if step.op == "derive_sum":
        total = 0.0
        for f in step.args["parts"]:
            v = row.get(f)
            if v is None:
                raise ConversionUngecognizable(_rid(row), f"missing component {f}")
            total += _number(v, _rid(row), f)
        if not math.isfinite(total):
            raise ConversionUngecognizable(_rid(row), "sum is not finite")
        out[step.args["to"]] = total
        return out
    if step.op == "code_translate":
        raw = row.get(step.args["from"])
        table = step.args["table"]
        try:
            known = raw in table
        except TypeError:
            raise ConversionUngecognizable(
                _rid(row), f"value of {step.args['from']} is not a valid code "
                           f"(unhashable {type(raw).__name__})") from None
        if not known:
            raise ConversionUngecognizable(_rid(row),
                                           f"value {raw!r} not in code table for {step.args['from']}")
        out[step.args["to"]] = table[raw]
        return out
    if step.op == "assert_not_null":
        if row.get(step.args["field"]) is None:
            raise ConversionUngecognizable(_rid(row), f"{step.args['field']} is null")
        return out
    raise CompilationError(f"unknown op {step.op}")


def compile_mapping(mapping: Mapping, steps: list[PlanStep]) -> TransformationPlan:
    problems = mapping.approval_problems()
    if problems:
        raise CompilationError("mapping must be approved before compilation: " + "; ".join(problems))
    frozen = tuple(steps)
    if not frozen:
        raise CompilationError("a transformation plan needs at least one step")
    for step in frozen:
        if not isinstance(step, PlanStep):
            raise CompilationError("steps must be PlanStep instances")
        _validate_step(step)
    return TransformationPlan(
        mapping_id=mapping.id,
        mapping_digest=mapping.digest(),
        target_artifact=mapping.target_artifact,
        steps=frozen,
        approved_by=mapping.approved_by,
        approval_ref=mapping.approval_ref,
        mapping_version=mapping.version,
    )


def compile_mapping_to_sql(mapping: Mapping, steps: list[PlanStep], *,
                           source_table: str, dialect: str = "postgres") -> str:
    """Emit an equivalent SELECT for the deterministic plan (spec §19:
    the compiler must be able to generate SQL, not only Python). The SQL is
    a *read-only* compilation of the mapping — traceability is preserved by
    embedding the mapping digest.

    KNOWN LIMITS (tracked in #30): not equivalent to Python failure semantics
    and does not safely quote identifiers/literals."""
    problems = mapping.approval_problems()
    if problems:
        raise CompilationError("mapping must be approved before compilation: " + "; ".join(problems))
    select_exprs: list[str] = []
    identity_cols: list[str] = []
    for step in steps:
        if step.op == "copy":
            select_exprs.append(f"{step.args['from']} AS {step.args['to']}")
        elif step.op == "derive_sum":
            parts = " + ".join(step.args["parts"])
            select_exprs.append(f"({parts}) AS {step.args['to']}")
        elif step.op == "code_translate":
            whens = " ".join(
                f"WHEN {k!r} THEN {v!r}" for k, v in step.args["table"].items())
            select_exprs.append(
                f"CASE {step.args['from']} {whens} ELSE NULL END AS {step.args['to']}")
        elif step.op == "assert_not_null":
            identity_cols.append(step.args["field"])
        else:
            raise CompilationError(f"no SQL lowering for op {step.op}")
    if not select_exprs:
        raise CompilationError("no compilable steps")
    where = ""
    if identity_cols:
        where = "\nWHERE " + " AND ".join(f"{c} IS NOT NULL" for c in identity_cols)
    digest = mapping.digest()
    return (f"-- compiled from mapping {mapping.id} digest={digest}\n"
            f"-- canonical concept: {mapping.canonical_concept}\n"
            f"SELECT {', '.join(select_exprs)}\nFROM {source_table}{where};")


def assertion_from_plan_output(plan: TransformationPlan, target: dict[str, Any],
                               provenance: Provenance, mapping: Mapping, *,
                               target_field: str | None = None) -> Assertion:
    """Wrap a converted target value as an assertion with lineage.

    The value is read by exact key (default: the plan's target artifact). A
    falsey value (0, 0.0, False, "") is a real value and is preserved; a
    missing key is an error — never substitute another field (#27)."""
    key = target_field if target_field is not None else plan.target_artifact
    if key not in target:
        raise LineageError(
            f"target field {key!r} absent from conversion output; "
            "refusing to substitute another field")
    return Assertion(
        concept=mapping.canonical_concept,
        value=target[key],
        derivation=DerivationStatus.DERIVED_VALUE,
        provenance=provenance,
        confidence=mapping.confidence,
        transformation_history=(plan.mapping_digest,),
        validation_state="pending",
    )
