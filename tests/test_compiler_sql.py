"""SQL lowering is fail-closed (spec §68, issue #30): ops whose Python
failure semantics cannot survive a single SELECT are refused instead of
silently weakened. Tests assert on refusal and on safe identifier/literal
quoting — not on fragile SQL substrings (#30)."""

import pytest
from helpers import approved_mapping
from sematik.compiler import (
    CompilationError,
    PlanStep,
    compile_mapping,
    compile_mapping_to_sql,
    quote_ident,
    quote_literal,
)
from sematik.mapping import Mapping
from sematik.model import Confidence, Provenance
from sematik.runner import run_conversion


def _approved():
    return approved_mapping(canonical_concept="Assessment.Valuation.total",
                            target_artifact="total_assessed")


def test_sql_lowering_emits_value_preserving_steps():
    """Only copy/rename lower (I-14). Behavioral equivalence with the Python
    backend is asserted by execution in test_sql_python_equivalence.py; this
    test only pins the emitted shape."""
    steps = [PlanStep("rename", {"from": "LNDVAL", "to": "land_value"}),
             PlanStep("copy", {"from": "APN", "to": "apn"})]
    sql = compile_mapping_to_sql(_approved(), steps, source_table="parcls")
    assert sql.startswith("-- compiled from mapping")
    assert '"LNDVAL" AS "land_value"' in sql
    assert '"APN" AS "apn"' in sql
    assert 'FROM "parcls"' in sql


# ---- #30: safe identifier/literal quoting ----------------------------------

def test_quote_ident_doubles_embedded_quotes():
    assert quote_ident('weird"name') == '"weird""name"'
    assert quote_ident("LNDVAL") == '"LNDVAL"'


def test_quote_ident_makes_reserved_words_safe():
    """A column literally named 'select' is valid when quoted."""
    assert quote_ident("select") == '"select"'
    assert quote_ident("from") == '"from"'


def test_quote_ident_supports_spaces_and_special_chars():
    assert quote_ident("column name") == '"column name"'
    assert quote_ident("col-name") == '"col-name"'
    assert quote_ident("col$name") == '"col$name"'


def test_quote_ident_rejects_empty_and_non_string():
    with pytest.raises(CompilationError, match="non-empty string"):
        quote_ident("")
    with pytest.raises(CompilationError, match="non-empty string"):
        quote_ident(123)   # type: ignore[arg-type]


def test_quote_ident_rejects_unsupported_dialect():
    with pytest.raises(CompilationError, match="unsupported SQL dialect"):
        quote_ident("col", dialect="mysql")


def test_sql_lowering_quotes_all_identifiers():
    """Every identifier in the generated SQL must be double-quoted (#30)."""
    steps = [PlanStep("copy", {"from": "col with space", "to": "select"}),
             PlanStep("rename", {"from": "val-1", "to": "total$amt"})]
    sql = compile_mapping_to_sql(_approved(), steps, source_table="my table")
    assert '"col with space" AS "select"' in sql
    assert '"val-1" AS "total$amt"' in sql
    assert 'FROM "my table"' in sql


def test_sql_lowering_rejects_unsafe_table_name():
    """source_table with an empty string raises rather than emitting
    invalid SQL (#30)."""
    with pytest.raises(CompilationError, match="non-empty string"):
        compile_mapping_to_sql(_approved(),
                               [PlanStep("copy", {"from": "a", "to": "b"})],
                               source_table="")


def test_sql_lowering_rejects_unsupported_dialect():
    with pytest.raises(CompilationError, match="unsupported SQL dialect"):
        compile_mapping_to_sql(_approved(),
                               [PlanStep("copy", {"from": "a", "to": "b"})],
                               source_table="t", dialect="oracle")


def test_quote_literal_doubles_embedded_single_quotes():
    assert quote_literal("REG") == "'REG'"
    assert quote_literal("O'Brien") == "'O''Brien'"
    assert quote_literal("it's a 'test'") == "'it''s a ''test'''"


def test_quote_literal_rejects_non_string():
    with pytest.raises(CompilationError, match="must be a string"):
        quote_literal(123)           # type: ignore[arg-type]
    with pytest.raises(CompilationError, match="must be a string"):
        quote_literal(None)          # type: ignore[arg-type]


# ---- #30: cross-target equivalence (Python vs SQL) ------------------------

def test_derive_sum_converts_in_python_and_is_refused_in_sql():
    """The Python backend sums exactly (int preserved); the SQL backend refuses
    derive_sum (I-14) because ``+`` cannot reproduce Python's rejections.
    Executed Python-vs-SQL comparisons live in test_sql_python_equivalence.py
    (this test used to compare SQL *substrings*, which proved nothing)."""
    steps = [PlanStep("copy", {"from": "APN", "to": "apn"}),
             PlanStep("derive_sum", {"parts": ["LNDVAL", "AV_IMP"], "to": "total_assessed"})]
    m = _approved()
    plan = compile_mapping(m, steps)
    rows = [{"_id": "r1", "APN": "A-1", "LNDVAL": 100, "AV_IMP": 50}]
    run = run_conversion(
        rows, plan, m, source_snapshot="s", domain_pack_version="p",
        engine_version="e",
        provenance_of=lambda r: Provenance(source_system="s", source_record=str(r["_id"])))
    assert run.converted == 1
    assert run.outputs[0]["total_assessed"] == 150     # int preserved
    with pytest.raises(CompilationError, match="no SQL lowering for derive_sum"):
        compile_mapping_to_sql(m, steps, source_table="src")


def test_python_and_sql_targets_agree_on_unmapped_case():
    """When code_translate rejects an unknown code, both targets refuse.
    SQL refuses at compile time rather than silently emitting NULL (#30)."""
    steps = [PlanStep("code_translate", {"from": "XFER", "to": "k",
                                         "table": {"REG": "regular"}})]
    m = _approved()
    # Python: compiles but rejects the row at runtime
    plan = compile_mapping(m, steps)
    rows = [{"_id": "r1", "XFER": "UNK9"}]
    run = run_conversion(
        rows, plan, m, source_snapshot="s", domain_pack_version="p",
        engine_version="e",
        provenance_of=lambda r: Provenance(source_system="s", source_record=str(r["_id"])))
    assert run.converted == 0 and run.rejected == 1
    # SQL: refuses at compile time (no silent CASE ... ELSE NULL)
    with pytest.raises(CompilationError, match="no SQL lowering"):
        compile_mapping_to_sql(m, steps, source_table="src")


def test_sql_lowering_requires_approval():
    m = Mapping(source_artifact="s", canonical_concept="c", approved_by="", confidence=Confidence(0))
    m.add_level(1, "physical", "x")
    with pytest.raises(CompilationError, match="approved"):
        compile_mapping_to_sql(m, [PlanStep("copy", {"from": "a", "to": "b"})], source_table="t")


@pytest.mark.parametrize("op,args", [
    ("code_translate", {"from": "XFER", "to": "transfer_kind",
                        "table": {"REG": "regular", "PT": "partial"}}),
    ("assert_not_null", {"field": "APN"}),
    ("derive_sum", {"parts": ["LNDVAL", "AV_IMP"], "to": "total_assessed"}),
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


# ---- #30 follow-up: SQL comment injection, rename lowering, step validation

def test_sql_comment_strips_newline_in_mapping_id():
    """mapping.id containing a newline must not break out of the SQL
    single-line comment — that would be SQL injection (#30 HIGH)."""
    m = _approved()
    m.id = "evil\nDROP TABLE users;"
    sql = compile_mapping_to_sql(m, [PlanStep("copy", {"from": "a", "to": "t"})],
                                 source_table="src")
    for line in sql.split("\n"):
        assert not line.strip().startswith("DROP"), f"SQL injection! line: {line!r}"


def test_sql_comment_strips_newline_in_canonical_concept():
    """canonical_concept containing a newline must not break out of the
    SQL comment (#30 HIGH)."""
    m = _approved()
    m.canonical_concept = "c\nDROP TABLE users;"
    sql = compile_mapping_to_sql(m, [PlanStep("copy", {"from": "a", "to": "t"})],
                                 source_table="src")
    for line in sql.split("\n"):
        assert not line.strip().startswith("DROP"), f"SQL injection! line: {line!r}"


def test_sql_lowering_handles_rename_op():
    """rename op lowers identically to copy — value-preserving alias (#30)."""
    steps = [PlanStep("rename", {"from": "old_name", "to": "new_name"})]
    sql = compile_mapping_to_sql(_approved(), steps, source_table="src")
    assert '"old_name" AS "new_name"' in sql


def test_sql_lowering_validates_steps():
    """compile_mapping_to_sql calls _validate_step for each step, so invalid
    steps raise CompilationError (not KeyError) (#30 LOW)."""
    with pytest.raises(CompilationError, match="missing required args"):
        compile_mapping_to_sql(_approved(),
                               [PlanStep("copy", {"from": "a"})],  # missing "to"
                               source_table="t")
