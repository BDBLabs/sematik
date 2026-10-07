"""SQL lowering is fail-closed (spec §68, issue #30): ops whose Python
failure semantics cannot survive a single SELECT are refused instead of
silently weakened. Tests assert on refusal, not SQL substrings."""

import pytest
from helpers import approved_mapping
from sematik.compiler import (
    CompilationError,
    PlanStep,
    compile_mapping,
    compile_mapping_to_sql,
)
from sematik.mapping import Mapping
from sematik.model import Confidence, Provenance
from sematik.runner import run_conversion


def _approved():
    return approved_mapping(canonical_concept="Assessment.Valuation.total",
                            target_artifact="total_assessed")


def test_sql_lowering_emits_value_preserving_steps():
    steps = [PlanStep("derive_sum", {"parts": ["LNDVAL", "AV_IMP"], "to": "total_assessed"}),
             PlanStep("copy", {"from": "APN", "to": "apn"})]
    sql = compile_mapping_to_sql(_approved(), steps, source_table="parcls")
    assert sql.startswith("-- compiled from mapping")
    assert "(LNDVAL + AV_IMP) AS total_assessed" in sql
    assert "APN AS apn" in sql
    assert "FROM parcls" in sql


def test_sql_lowering_requires_approval():
    m = Mapping(source_artifact="s", canonical_concept="c", approved_by="", confidence=Confidence(0))
    m.add_level(1, "physical", "x")
    with pytest.raises(CompilationError, match="approved"):
        compile_mapping_to_sql(m, [PlanStep("copy", {"from": "a", "to": "b"})], source_table="t")


@pytest.mark.parametrize("op,args", [
    ("code_translate", {"from": "XFER", "to": "transfer_kind",
                        "table": {"REG": "regular", "PT": "partial"}}),
    ("assert_not_null", {"field": "APN"}),
])
def test_sql_lowering_refuses_divergent_ops(op, args):
    """Refusal rationale: Python rejects unknown codes and null rows as
    explicit per-record exceptions; CASE...ELSE NULL and WHERE filters
    would silently absorb them (#30)."""
    with pytest.raises(CompilationError, match="no SQL lowering"):
        compile_mapping_to_sql(_approved(), [PlanStep(op, args)], source_table="t")


def test_python_backend_rejects_what_sql_cannot_represent():
    """Equivalence rationale: these are the exact rows SQL used to swallow.
    Python rejects both explicitly, so refusing the lowering loses nothing
    that was ever faithfully convertible."""
    m = approved_mapping(canonical_concept="c", target_artifact="t")
    plan = compile_mapping(m, [
        PlanStep("copy", {"from": "a", "to": "t"}),
        PlanStep("code_translate", {"from": "X", "to": "k", "table": {"REG": "regular"}}),
        PlanStep("assert_not_null", {"field": "a"}),
    ])
    run = run_conversion(
        [{"a": 1, "X": "UNK9", "_id": "bad-code"},
         {"a": None, "X": "REG", "_id": "null-id"}],
        plan, m, source_snapshot="s", domain_pack_version="p", engine_version="e",
        provenance_of=lambda r: Provenance(source_system="s", source_record=str(r["_id"])))
    assert run.converted == 0 and run.rejected == 2
