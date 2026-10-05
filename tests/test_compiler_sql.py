from sematik.compiler import PlanStep, compile_mapping_to_sql
from sematik.mapping import Mapping
from sematik.model import Confidence
from helpers import approved_mapping


def _approved():
    return approved_mapping(canonical_concept="Assessment.Valuation.total",
                            target_artifact="total_assessed")


def test_sql_lowering_contains_all_steps():
    steps = [PlanStep("derive_sum", {"parts": ["LNDVAL", "AV_IMP"], "to": "total_assessed"}),
             PlanStep("copy", {"from": "APN", "to": "apn"}),
             PlanStep("code_translate", {"from": "XFER", "to": "transfer_kind",
                                          "table": {"REG": "regular", "PT": "partial"}}),
             PlanStep("assert_not_null", {"field": "APN"})]
    sql = compile_mapping_to_sql(_approved(), steps, source_table="parcls")
    assert sql.startswith("-- compiled from mapping")
    assert "(LNDVAL + AV_IMP) AS total_assessed" in sql
    assert "APN AS apn" in sql
    assert "CASE XFER WHEN 'REG' THEN 'regular'" in sql
    assert "WHERE APN IS NOT NULL" in sql
    assert "FROM parcls" in sql


def test_sql_lowering_requires_approval():
    m = Mapping(source_artifact="s", canonical_concept="c", approved_by="", confidence=Confidence(0))
    m.add_level(1, "physical", "x")
    try:
        compile_mapping_to_sql(m, [PlanStep("copy", {"from": "a", "to": "b"})], source_table="t")
        assert False, "expected CompilationError"
    except Exception as e:
        assert "approved" in str(e)
