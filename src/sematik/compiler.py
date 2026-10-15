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
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, TYPE_CHECKING

from .mapping import Mapping
from .model import Assertion, DerivationStatus, Provenance

if TYPE_CHECKING:
    from .control import VerifiedApproval


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
    approval_digest: str = ""  # Content digest of the approval event (ADR-0008)

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))

    def digest(self) -> str:
        """Content digest over everything that determines behavior and the
        approval the plan was compiled under (full SHA-256).

        Content only (I-13, spec §22/§69): ``mapping_id`` is a generated
        identifier and is deliberately excluded, otherwise identical inputs
        would yield a different manifest hash in every process. Instance
        binding is still enforced at run time by :meth:`bound_to`.
        
        Includes approval_digest for governance audit trail (ADR-0008)."""
        payload = json.dumps({
            "mapping_digest": self.mapping_digest,
            "target": self.target_artifact,
            "steps": [{"op": s.op, "args": _canon(s.args)} for s in self.steps],
            "approved_by": self.approved_by, "approval_ref": self.approval_ref,
            "mapping_version": self.mapping_version,
            "approval_digest": self.approval_digest,
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


def _parse_numeric_string(raw: str, rid: str, name: str) -> int | Decimal | float:
    """Parse a string to the most appropriate exact numeric type (#31).

    Order of preference:
    1. ``int``  — preserves integers above IEEE-754 exact range (e.g. 10**400).
    2. ``Decimal`` — preserves exact decimal arithmetic for financial values
       (``0.1 + 0.2 == 0.3``, not ``0.30000000000000004``).
    3. ``float`` — only for inputs that are genuinely float (e.g. hex floats).
    """
    if not raw:
        raise ConversionUngecognizable(rid, f"component {name} is not numeric")
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        d = Decimal(raw)
        if not d.is_finite():
            raise ConversionUngecognizable(rid, f"component {name} is not finite")
        return d
    except InvalidOperation:
        pass
    try:
        f = float(raw)
    except (ValueError, OverflowError):
        raise ConversionUngecognizable(rid, f"component {name} is not numeric") from None
    if not math.isfinite(f):
        raise ConversionUngecognizable(rid, f"component {name} is not finite")
    return f


def _number(value: Any, rid: str, name: str) -> int | Decimal | float:
    """Coerce a derived input to a numeric form, preserving exactness (#31).

    Integers stay ``int``, Decimals stay ``Decimal``, floats stay ``float`` —
    no silent ``float()`` coercion that loses precision.  String inputs are
    parsed to ``int`` or ``Decimal`` (preferred) before falling back to
    ``float``.
    """
    if isinstance(value, bool):
        raise ConversionUngecognizable(rid, f"component {name} is boolean, not numeric")
    if isinstance(value, (int, float, Decimal)):
        number = value
    elif isinstance(value, str):
        number = _parse_numeric_string(value, rid, name)
    else:
        raise ConversionUngecognizable(
            rid, f"component {name} has unsupported type {type(value).__name__}")
    if isinstance(number, float) and not math.isfinite(number):
        raise ConversionUngecognizable(rid, f"component {name} is not finite")
    if isinstance(number, Decimal) and not number.is_finite():
        raise ConversionUngecognizable(rid, f"component {name} is not finite")
    return number


def _apply_derive_sum(step: PlanStep, row: dict[str, Any]) -> int | Decimal | float:
    """Accumulate component values with exactness-preserving types (#31).

    Starts from ``int`` 0, so ``int + int → int``, ``int + Decimal → Decimal``,
    ``int + float → float``.  Mixing ``Decimal`` and ``float`` in the same
    sum is rejected as incompatible (fail-closed, spec §68).
    """
    total: int | Decimal | float = 0
    for f in step.args["parts"]:
        v = row.get(f)
        if v is None:
            raise ConversionUngecognizable(_rid(row), f"missing component {f}")
        num = _number(v, _rid(row), f)
        try:
            total += num
        except TypeError as exc:
            raise ConversionUngecognizable(
                _rid(row),
                f"incompatible numeric types in derive_sum {num!r} + {total!r}: {exc}") from None
    if isinstance(total, Decimal):
        if not total.is_finite():
            raise ConversionUngecognizable(_rid(row), "sum is not finite")
    elif not math.isfinite(total):
        raise ConversionUngecognizable(_rid(row), "sum is not finite")
    return total


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
        out[step.args["to"]] = _apply_derive_sum(step, row)
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


def compile_mapping(mapping: Mapping, steps: list[PlanStep], 
                    approval: VerifiedApproval | None = None) -> TransformationPlan:
    """Compile a mapping with steps into a deterministic plan (spec §19).

    Args:
        mapping: The mapping to compile
        steps: List of transformation steps
        approval: Optional VerifiedApproval token from Control store.
                  When provided, enforces I-11/I-12 governance requirements.

    Returns:
        TransformationPlan with immutable steps and content digest

    Raises:
        CompilationError: If mapping is not approved or has structural problems
    """
    problems = mapping.approval_problems()
    if problems:
        raise CompilationError("mapping must be approved before compilation: " + "; ".join(problems))
    
    # If approval token provided, verify integrity (ADR-0008 §3)
    if approval is not None:
        if approval.mapping_digest != mapping.digest():
            raise CompilationError(
                f"approval mapping digest mismatch: approval has {approval.mapping_digest}, "
                f"mapping has {mapping.digest()}")
        if approval.plan_digest:  # Could be empty if not yet compiled
            # Plan digest not yet known, will be set later
            pass
    
    frozen = tuple(steps)
    if not frozen:
        raise CompilationError("a transformation plan needs at least one step")
    for step in frozen:
        if not isinstance(step, PlanStep):
            raise CompilationError("steps must be PlanStep instances")
        _validate_step(step)
    
    plan = TransformationPlan(
        mapping_id=mapping.id,
        mapping_digest=mapping.digest(),
        target_artifact=mapping.target_artifact,
        steps=frozen,
        approved_by=mapping.approved_by,
        approval_ref=mapping.approval_ref,
        mapping_version=mapping.version,
        approval_digest=approval.approval_digest if approval else "",
    )
    return plan


_SQL_DIALECTS = {"postgres", "sqlite", "duckdb"}


def quote_ident(name: str, dialect: str = "postgres") -> str:
    """Safely quote a SQL identifier (column or table name) (#30).

    PostgreSQL/SQLite/DuckDB all use the SQL-standard double-quote
    identifier delimiter.  Embedded double-quotes are escaped by doubling
    them (e.g. ``weird"name`` → ``"weird""name"``).  This makes **any**
    string — including reserved words, names with spaces, or values
    containing special characters — safe as an identifier reference.

    >>> quote_ident("LNDVAL")
    '"LNDVAL"'
    >>> quote_ident('select')
    '"select"'
    >>> quote_ident('weird"name')
    '"weird""name"'
    """
    if dialect not in _SQL_DIALECTS:
        raise CompilationError(f"unsupported SQL dialect: {dialect!r}")
    if not isinstance(name, str) or not name:
        raise CompilationError(f"identifier must be a non-empty string, got {name!r}")
    return f'"{name.replace(chr(34), chr(34) * 2)}"'


def quote_literal(value: str, dialect: str = "postgres") -> str:
    """Safely quote a SQL string literal (#30).

    Uses the SQL-standard single-quote literal with doubled embedded
    quotes (``O'Brien`` → ``'O''Brien'``).  Non-string values are rejected
    — callers must convert to string explicitly, preventing accidental
    type coercion in generated SQL.

    >>> quote_literal("REG")
    "'REG'"
    >>> quote_literal("O'Brien")
    "'O''Brien'"
    """
    if dialect not in _SQL_DIALECTS:
        raise CompilationError(f"unsupported SQL dialect: {dialect!r}")
    if not isinstance(value, str):
        raise CompilationError(
            f"literal must be a string, got {type(value).__name__}: {value!r}")
    return f"'{value.replace(chr(39), chr(39) * 2)}'"


def _sanitize_for_comment(value: Any) -> str:
    """Strip control characters from a string for safe embedding in a SQL
    single-line comment (#30).

    SQL ``--`` comments are single-line — any newline character terminates the
    comment and allows subsequent text to be parsed as SQL code.  This is a
    comment-injection vector that can escalate to SQL injection if the
    embedded value comes from user-provided Mapping fields (``mapping.id``,
    ``canonical_concept``).

    All control characters (0x00–0x1f, 0x7f) are removed to ensure the
    value cannot break out of the ``--`` comment delimiter.
    """
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r"[\x00-\x1f\x7f]", "", value)


def compile_mapping_to_sql(mapping: Mapping, steps: list[PlanStep], *,
                           source_table: str, dialect: str = "postgres") -> str:
    """Emit an equivalent SELECT for the deterministic plan (spec §19:
    the compiler must be able to generate SQL, not only Python). The SQL is
    a *read-only* compilation of the mapping — traceability is preserved by
    embedding the mapping digest.

    Fail-closed (spec §68, issue #30): ops whose Python failure semantics
    cannot be preserved in a single SELECT are refused rather than silently
    weakened.  Only value-preserving lowering is emitted.  All identifiers
    (column names, target aliases, table names) are safely quoted via
    ``quote_ident`` — names containing reserved words, spaces, or special
    characters are handled correctly.  Metadata embedded in SQL single-line
    comments is sanitized to strip control characters, preventing
    comment-injection from user-provided Mapping fields."""
    problems = mapping.approval_problems()
    if problems:
        raise CompilationError("mapping must be approved before compilation: " + "; ".join(problems))
    if dialect not in _SQL_DIALECTS:
        raise CompilationError(f"unsupported SQL dialect: {dialect!r}")
    select_exprs: list[str] = []
    for step in steps:
        _validate_step(step)
        if step.op == "copy":
            src = quote_ident(step.args["from"], dialect)
            dst = quote_ident(step.args["to"], dialect)
            select_exprs.append(f"{src} AS {dst}")
        elif step.op == "rename":
            # Semantically identical to copy (#30): target alias replaces source.
            src = quote_ident(step.args["from"], dialect)
            dst = quote_ident(step.args["to"], dialect)
            select_exprs.append(f"{src} AS {dst}")
        elif step.op == "derive_sum":
            raise CompilationError(
                f"no SQL lowering for derive_sum on {step.args['to']!r}: "
                "Python rejects missing/None components as explicit exceptions; "
                "SQL (a + b) silently returns NULL for any NULL operand; "
                "refusing rather than weakening failure semantics (#30)")
        elif step.op == "code_translate":
            raise CompilationError(
                f"no SQL lowering for code_translate on {step.args['from']!r}: "
                "Python rejects unmapped codes as explicit exceptions (spec §68) "
                "but CASE ... ELSE NULL would silently convert them to NULL; "
                "refusing rather than weakening failure semantics (#30)")
        elif step.op == "assert_not_null":
            raise CompilationError(
                f"no SQL lowering for assert_not_null on {step.args['field']!r}: "
                "Python rejects null rows as explicit per-record exceptions but "
                "WHERE ... IS NOT NULL would silently drop them, breaking "
                "converted + rejected == total accounting; "
                "refusing rather than weakening failure semantics (#30)")
        else:
            raise CompilationError(f"no SQL lowering for op {step.op}")
    if not select_exprs:
        raise CompilationError("no compilable steps")
    digest = mapping.digest()
    table = quote_ident(source_table, dialect)
    # Sanitize user-provided values before embedding in SQL comments —
    # newlines in mapping.id/canonical_concept would break out of the
    # "--" comment and escalate to SQL injection (#30).
    safe_id = quote_literal(_sanitize_for_comment(mapping.id), dialect)
    safe_concept = quote_literal(_sanitize_for_comment(mapping.canonical_concept), dialect)
    return (f"-- compiled from mapping {safe_id} digest={digest}\n"
            f"-- canonical concept: {safe_concept}\n"
            f"SELECT {', '.join(select_exprs)}\nFROM {table};")


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
        transformation_history=(plan.mapping_digest, plan.digest()),
        validation_state="pending",
    )
