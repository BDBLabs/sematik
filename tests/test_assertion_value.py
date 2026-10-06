"""Regression: assertion_from_plan_output must require the exact target key
and preserve falsy values (review finding: {'other':99,'t':0} yielded 99).
Spec §68: fail visibly, never silently substitute.
"""

import pytest
from sematik.compiler import (
    ConversionUngecognizable,
    PlanStep,
    assertion_from_plan_output,
    compile_mapping,
)
from sematik.mapping import Mapping
from sematik.model import Confidence, Provenance


def _mapping_target_t():
    m = Mapping(
        source_artifact="s",
        canonical_concept="c",
        target_artifact="t",
        approved_by="t",
        confidence=Confidence(0.9),
    )
    m.add_level(1, "physical", "x")
    return m


def _plan_t():
    return compile_mapping(
        _mapping_target_t(), [PlanStep("copy", {"from": "a", "to": "t"})]
    )


def _prov(record="r1"):
    return Provenance(source_system="s", source_record=record)


def test_zero_value_preserved_not_replaced():
    plan = _plan_t()
    a = assertion_from_plan_output(
        plan, {"other": 99, "t": 0}, _prov(), _mapping_target_t()
    )
    assert a.value == 0


def test_falsy_values_preserved():
    plan = _plan_t()
    mapping = _mapping_target_t()
    assert assertion_from_plan_output(plan, {"t": ""}, _prov(), mapping).value == ""
    assert assertion_from_plan_output(plan, {"t": False}, _prov(), mapping).value is False
    assert assertion_from_plan_output(plan, {"t": None}, _prov(), mapping).value is None


def test_missing_target_key_raises_visibly():
    plan = _plan_t()
    with pytest.raises(ConversionUngecognizable):
        assertion_from_plan_output(plan, {"other": 99}, _prov(), _mapping_target_t())
