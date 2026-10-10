"""Regression tests for the approval → plan → execution → lineage chain.

Each test reproduces a concrete counterexample from issues #24, #25, #26, #27
and #35 against the real execution path (not substring checks)."""

import math
from decimal import Decimal

import pytest
from helpers import approved_mapping, prov

from sematik.compiler import (CompilationError, LineageError, PlanStep,
                              TransformationPlan, assertion_from_plan_output,
                              compile_mapping)
from sematik.mapping import Mapping
from sematik.model import Confidence, Provenance
from sematik.runner import run_conversion


def _run(rows, plan, mapping, **kw):
    kw.setdefault("provenance_of", prov)
    return run_conversion(rows, plan, mapping, source_snapshot="snap",
                          domain_pack_version="p", engine_version="e", **kw)


def _copy_plan(src="x", dst="t"):
    m = approved_mapping(target_artifact=dst)
    return m, compile_mapping(m, [PlanStep("copy", {"from": src, "to": dst})])


# ---- #24: approval is complete, not an actor string -----------------------

def test_actor_string_alone_cannot_compile():
    m = Mapping(source_artifact="s", canonical_concept="c", target_artifact="t",
                approved_by="anyone", confidence=Confidence(0.001))
    with pytest.raises(CompilationError, match="approved"):
        compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])


@pytest.mark.parametrize("field,value,fragment", [
    ("approved_by", "", "approver"),
    ("approval_ref", " ", "approval reference"),
    ("version", "", "version"),
    ("evidence_refs", [], "evidence"),
    ("golden_plan_digest", "", "golden"),
    ("blocking_question_ids", ["Q-1"], "blocking questions"),
])
def test_each_approval_element_is_required(field, value, fragment):
    m = approved_mapping(**{field: value})
    assert not m.approved()
    with pytest.raises(CompilationError, match=fragment):
        compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])


def test_incomplete_mapping_cannot_compile():
    m = approved_mapping()
    m.levels.pop()
    with pytest.raises(CompilationError, match="levels missing"):
        compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])


def test_unknown_op_and_missing_args_fail_at_compile_time():
    m = approved_mapping()
    with pytest.raises(CompilationError, match="unknown op"):
        compile_mapping(m, [PlanStep("explode", {})])
    with pytest.raises(CompilationError, match="missing required args"):
        compile_mapping(m, [PlanStep("copy", {"from": "x"})])


def test_evidence_and_golden_fields_appear_in_digest():
    """Evidence refs and golden plan digest are part of the mapping's content
    fingerprint: changing either changes the digest (#24)."""
    from dataclasses import replace
    m = approved_mapping()
    base = m.digest()
    assert replace(m, evidence_refs=["evidence:changed"]).digest() != base
    assert replace(m, golden_plan_digest="golden:changed").digest() != base
    assert replace(m, blocking_question_ids=[]).digest() == base  # empty → no change


def test_evidence_change_invalidates_plan_binding():
    """A plan compiled under one evidence set must not run against a mapping
    whose evidence has changed — the plan must be recompiled and re-approved
    (#24)."""
    from dataclasses import replace
    m = approved_mapping()
    p = compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])
    assert p.bound_to(m)
    m_changed = replace(m, evidence_refs=["evidence:changed"])
    assert not p.bound_to(m_changed)


def test_golden_plan_digest_change_invalidates_plan_binding():
    """Changing the golden plan reference invalidates the compiled plan,
    requiring recompilation under the new tested plan (#24)."""
    from dataclasses import replace
    m = approved_mapping()
    p = compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])
    m_changed = replace(m, golden_plan_digest="golden:updated")
    assert not p.bound_to(m_changed)


def test_run_refuses_when_evidence_changes_after_compilation():
    """After compilation, changing the evidence refs makes the plan unbound —
    even though the mapping is still structurally approved, the plan's
    embedded mapping digest no longer matches, so the run refuses rather
    than executing under stale evidence (#24)."""
    from dataclasses import replace
    m = approved_mapping()
    p = compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])
    # Still approved (has evidence + golden + 7 levels) but different digest
    m_changed = replace(m, evidence_refs=["evidence:changed"])
    assert m_changed.approved()
    with pytest.raises(CompilationError, match="not bound"):
        _run([{"_id": 1, "x": 1}], p, m_changed)


# ---- #24 (cont.): content validation on evidence & question refs --------

@pytest.mark.parametrize("bad_refs", [[""], ["   "], ["ok", ""]])
def test_evidence_refs_with_empty_strings_rejected_at_construction(bad_refs):
    """Empty or whitespace-only evidence refs are a programming error and
    must be rejected at construction (fail-fast), not silently accepted
    (#24 follow-up to cross-model review)."""
    with pytest.raises(ValueError, match="evidence_refs"):
        approved_mapping(evidence_refs=bad_refs)


@pytest.mark.parametrize("bad_refs", [[""], ["   "], ["Q-1", ""]])
def test_blocking_question_ids_with_empty_strings_rejected_at_construction(bad_refs):
    """Same content-validation guard applies to blocking_question_ids (#24)."""
    with pytest.raises(ValueError, match="blocking_question_ids"):
        approved_mapping(blocking_question_ids=bad_refs)


def test_empty_evidence_refs_rejected_by_approval_not_construction():
    """An empty list is valid at construction (it means 'no evidence yet')
    but must be caught by approval_problems() (#24)."""
    m = approved_mapping(evidence_refs=[])
    assert any("evidence" in p for p in m.approval_problems())


def test_mutation_to_empty_evidence_caught_by_approval():
    """Defense-in-depth: since Mapping is not frozen, a caller could mutate
    evidence_refs after construction. approval_problems() must still catch
    empty/whitespace entries (#24)."""
    m = approved_mapping()
    m.evidence_refs = [""]               # direct mutation, bypasses __post_init__
    assert not m.approved()
    assert any("evidence" in p for p in m.approval_problems())

    m.blocking_question_ids = ["Q-1"]   # valid unresolved question, bypasses __post_init__
    assert any("blocking questions" in p for p in m.approval_problems())


# ---- #25: immutable plans, content-bound manifest -------------------------

def test_plan_steps_are_immutable_and_isolated_from_caller():
    m = approved_mapping()
    args = {"from": "x", "to": "t"}
    plan = compile_mapping(m, [PlanStep("copy", args)])
    digest = plan.digest()
    args["from"] = "y"                      # caller mutates its own dict
    assert plan.digest() == digest
    with pytest.raises(TypeError):
        plan.steps[0].args["from"] = "y"    # cannot mutate in place
    with pytest.raises(Exception):
        plan.steps[0].args = {}             # frozen dataclass
    assert isinstance(plan.steps, tuple)


def test_manifest_changes_when_plan_changes_even_if_outputs_match():
    rows = [{"_id": 1, "x": 5, "z": 5}]
    m1, p1 = _copy_plan("x")
    m2, p2 = _copy_plan("z")
    r1, r2 = _run(rows, p1, m1), _run(rows, p2, m2)
    assert r1.outputs == r2.outputs and r1.converted == r2.converted
    assert r1.manifest_hash() != r2.manifest_hash()


def test_manifest_changes_when_source_content_changes_with_same_counts():
    m, p = _copy_plan()
    r1 = _run([{"_id": 1, "x": 1}], p, m)
    r2 = _run([{"_id": 1, "x": 2}], p, m)
    assert r1.manifest_hash() != r2.manifest_hash()


def test_manifest_is_deterministic_for_identical_inputs():
    rows = [{"_id": i, "x": i} for i in range(5)]
    m, p = _copy_plan()
    assert _run(rows, p, m).manifest_hash() == _run(rows, p, m).manifest_hash()


def test_run_refuses_plan_when_mapping_changed_after_compilation():
    m, p = _copy_plan()
    m.levels[0] = type(m.levels[0])(level=1, kind="physical", statement="CHANGED")
    with pytest.raises(CompilationError, match="not bound"):
        _run([{"_id": 1, "x": 1}], p, m)


def test_run_refuses_plan_when_approval_changed_after_compilation():
    m, p = _copy_plan()
    m.approval_ref = "FORGED-2"
    with pytest.raises(CompilationError, match="not bound"):
        _run([{"_id": 1, "x": 1}], p, m)


def test_run_refuses_unapproved_mapping():
    m, p = _copy_plan()
    m.approved_by = ""
    with pytest.raises(CompilationError, match="unapproved"):
        _run([{"_id": 1, "x": 1}], p, m)


# ---- #26: lineage emitted on the real execution path ----------------------

def test_run_emits_source_bound_assertions_for_every_converted_record():
    m, p = _copy_plan()
    rows = [{"_id": "a", "x": 1}, {"_id": "b", "x": 2}]
    run = _run(rows, p, m)
    assert run.converted == 2 and len(run.assertions) == 2
    assert [a.provenance.source_record for a in run.assertions] == ["a", "b"]
    assert [a.value for a in run.assertions] == [1, 2]
    assert all(p.mapping_digest in a.transformation_history for a in run.assertions)
    assert all(p.digest() in a.transformation_history for a in run.assertions)


@pytest.mark.parametrize("bad_provenance", [lambda r: None, lambda r: Provenance("")])
def test_record_without_provenance_is_rejected_not_converted(bad_provenance):
    m, p = _copy_plan()
    run = _run([{"_id": 1, "x": 1}], p, m, provenance_of=bad_provenance)
    assert run.converted == 0 and run.rejected == 1 and run.outputs == []
    assert run.exceptions[0].phase == "lineage"


def test_provenance_resolver_is_required():
    m, p = _copy_plan()
    with pytest.raises(CompilationError, match="provenance_of is required"):
        _run([{"_id": 1, "x": 1}], p, m, provenance_of=None)


def test_provenance_resolver_failure_rejects_record_and_continues():
    m, p = _copy_plan()

    def flaky(row):
        if row["_id"] == 1:
            raise RuntimeError("lookup down")
        return prov(row)
    run = _run([{"_id": 1, "x": 1}, {"_id": 2, "x": 2}], p, m, provenance_of=flaky)
    assert (run.converted, run.rejected) == (1, 1)


# ---- #27: falsey values preserved, no substituted field -------------------

@pytest.mark.parametrize("value", [0, 0.0, False, ""])
def test_assertion_preserves_falsey_target_values(value):
    m, p = _copy_plan()
    a = assertion_from_plan_output(p, {"other": 99, "t": value}, Provenance("s"), m)
    assert a.value == value and type(a.value) is type(value)


def test_assertion_requires_the_declared_target_key():
    m, p = _copy_plan()
    with pytest.raises(LineageError, match="refusing to substitute"):
        assertion_from_plan_output(p, {"other": 99}, Provenance("s"), m)


def test_zero_valued_conversion_keeps_zero_through_the_run():
    m, p = _copy_plan()
    run = _run([{"_id": 1, "x": 0}], p, m)
    assert run.assertions[0].value == 0 and run.outputs == [{"t": 0}]


def test_run_rejects_record_when_output_lacks_declared_target():
    m = approved_mapping(target_artifact="total")
    p = compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "something_else"})])
    run = _run([{"_id": 1, "x": 1}], p, m)
    assert run.converted == 0 and run.exceptions[0].phase == "lineage"


# ---- #35: bad rows are rejected per record; the batch continues -----------

def _sum_plan():
    m = approved_mapping(target_artifact="s")
    return m, compile_mapping(m, [PlanStep("derive_sum", {"parts": ["a", "b"], "to": "s"})])


@pytest.mark.parametrize("bad", ["abc", "nan", float("inf"), float("nan"),
                                 True, [1], {"k": 1}, Decimal("NaN"), None])
def test_derive_sum_rejects_unusable_values_and_batch_continues(bad):
    m, p = _sum_plan()
    rows = [{"_id": 1, "a": 1, "b": 2}, {"_id": 2, "a": bad, "b": 2}, {"_id": 3, "a": 4, "b": 5}]
    run = _run(rows, p, m)
    assert (run.converted, run.rejected, run.total_records) == (2, 1, 3)
    assert run.exceptions[0].record_id == "2"
    assert [o["s"] for o in run.outputs] == [3, 9]          # int preserved (#31)
    assert all(math.isfinite(o["s"]) for o in run.outputs)


# ---- #31: exact numeric semantics preservation -----------------------------

def test_derive_sum_preserves_large_integers():
    """Integers above IEEE-754 exact range survive unchanged (#31)."""
    m, p = _sum_plan()
    big = 10 ** 40
    rows = [{"_id": 1, "a": big, "b": 2}]
    run = _run(rows, p, m)
    assert len(run.outputs) == 1
    assert run.outputs[0]["s"] == big + 2
    assert isinstance(run.outputs[0]["s"], int)


def test_derive_sum_preserves_decimal_exactness():
    """0.1 + 0.2 == 0.3 with Decimal, not 0.30000000000000004 (#31)."""
    m, p = _sum_plan()
    rows = [{"_id": 1, "a": Decimal("0.1"), "b": Decimal("0.2")}]
    run = _run(rows, p, m)
    result = run.outputs[0]["s"]
    assert result == Decimal("0.3")
    assert isinstance(result, Decimal)


def test_derive_sum_float_input_yields_float():
    """A genuine float input propagates float semantics (0.1 + 0.2 != 0.3
    is the user's responsibility, not the engine's) (#31)."""
    m, p = _sum_plan()
    rows = [{"_id": 1, "a": 0.1, "b": 0.2}]
    run = _run(rows, p, m)
    result = run.outputs[0]["s"]
    assert isinstance(result, float)
    assert abs(result - 0.3) < 1e-15


def test_derive_sum_rejects_mixed_decimal_and_float():
    """Decimal + float is an incompatible exactness representation and must
    be rejected, not silently coerced (#31)."""
    m, p = _sum_plan()
    rows = [{"_id": 1, "a": Decimal("0.1"), "b": 0.2}]
    run = _run(rows, p, m)
    assert run.converted == 0
    assert run.rejected == 1
    assert "incompatible" in run.exceptions[0].reason


def test_derive_sum_string_parsing_preserves_types():
    """String inputs are parsed to int or Decimal, not float (#31)."""
    m, p = _sum_plan()
    rows = [
        {"_id": 1, "a": "100", "b": "2"},          # int + int → int
        {"_id": 2, "a": "0.10", "b": "0.20"},      # Decimal + Decimal → Decimal
    ]
    run = _run(rows, p, m)
    assert isinstance(run.outputs[0]["s"], int)
    assert run.outputs[0]["s"] == 102
    assert isinstance(run.outputs[1]["s"], Decimal)
    assert run.outputs[1]["s"] == Decimal("0.30")


def test_derive_sum_empty_string_and_whitespace_rejected():
    """Empty / whitespace-only strings are not numeric (#31)."""
    m, p = _sum_plan()
    rows = [{"_id": 1, "a": "", "b": 2}, {"_id": 2, "a": "   ", "b": 2}]
    run = _run(rows, p, m)
    assert (run.converted, run.rejected) == (0, 2)


def test_unhashable_code_value_rejected_and_batch_continues():
    m = approved_mapping(target_artifact="o")
    p = compile_mapping(m, [PlanStep("code_translate",
                                     {"from": "c", "to": "o", "table": {"A": 1}})])
    rows = [{"_id": 1, "c": "A"}, {"_id": 2, "c": ["bad"]}, {"_id": 3, "c": "A"}]
    run = _run(rows, p, m)
    assert (run.converted, run.rejected) == (2, 1)


def test_accounting_invariant_holds_for_mixed_batch():
    m, p = _sum_plan()
    rows = [{"_id": 1, "a": 1, "b": 1}, {"_id": 2}, "not-a-row", {"_id": 4, "a": None, "b": 1}]
    run = _run(rows, p, m)
    assert run.converted + run.rejected == run.total_records == 4


def test_defective_plan_fails_the_run_loudly():
    m = approved_mapping()
    bad = TransformationPlan(mapping_id=m.id, mapping_digest=m.digest(),
                             target_artifact="t", steps=(PlanStep("explode", {}),),
                             approved_by=m.approved_by, approval_ref=m.approval_ref,
                             mapping_version=m.version)
    with pytest.raises(CompilationError, match="unknown op"):
        _run([{"_id": 1}], bad, m)


def test_generic_system_provenance_without_source_record_is_rejected():
    m, p = _copy_plan()
    run = _run(
        [{"_id": "row-1", "x": 1}],
        p,
        m,
        provenance_of=lambda row: Provenance(
            source_system="legacy",
            source_table="T",
        ),
    )
    assert run.converted == 0
    assert run.rejected == 1
    assert run.exceptions[0].phase == "lineage"
    assert "source_record" in run.exceptions[0].reason


def test_execution_rejection_retains_record_provenance():
    m = approved_mapping(target_artifact="o")
    p = compile_mapping(
        m,
        [PlanStep(
            "code_translate",
            {"from": "c", "to": "o", "table": {"A": 1}},
        )],
    )
    run = _run([{"_id": "bad-2", "c": "UNKNOWN"}], p, m)
    assert run.converted == 0
    assert run.rejected == 1
    assert run.exceptions[0].phase == "execution"
    assert run.exceptions[0].provenance_ref == "legacy/T/bad-2"


def test_assertion_history_binds_mapping_and_exact_plan():
    m, p = _copy_plan()
    run = _run([{"_id": "row-1", "x": 7}], p, m)
    history = run.assertions[0].transformation_history
    assert m.digest() in history
    assert p.digest() in history


@pytest.mark.parametrize(
    "level,kind,statement,error",
    [
        (1, "physical-again", "duplicate level", "duplicated"),
        (8, "extra", "out of range", "out of range"),
    ],
)
def test_duplicate_or_out_of_range_semantic_levels_cannot_compile(
    level, kind, statement, error
):
    m = approved_mapping()
    m.add_level(level, kind, statement)
    assert not m.complete()
    with pytest.raises(CompilationError, match=error):
        compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])


def test_mapping_digest_is_full_sha256():
    m = approved_mapping()
    digest = m.digest()
    assert len(digest) == 64
    int(digest, 16)
