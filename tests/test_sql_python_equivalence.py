"""I-14 / #30: SQL lowering is verified by *executing* it, not by substring.

The first reviewer asked for exactly this (requests/2026-10-05-review-request.md,
HIGH item 6: "execute equivalence tests rather than checking SQL substrings").
#30 refused two ops but left `derive_sum` lowered and every equivalence test
string-matched, so a divergence survived. Each test here runs the emitted SQL on
an in-memory SQLite database and compares it with the Python backend on the
same rows.

SQLite validates the *shared* SQL constructs; it is not a PostgreSQL
validation. Its coercion rules are, if anything, laxer than PostgreSQL's, which
is why it is a good place for silent divergence to show up.
"""

import sqlite3

import pytest
from helpers import approved_mapping, prov
from sematik.compiler import (
    _REQUIRED_ARGS,
    CompilationError,
    PlanStep,
    compile_mapping,
    compile_mapping_to_sql,
)
from sematik.runner import run_conversion

# Ops that have an executed Python-vs-SQL equivalence test in this module.
# Adding an op to this set without a test below is a review failure.
DIFFERENTIAL_COVERED = {"copy", "rename"}

# One valid argument set per op. The guard test below fails when a new op is
# added to the compiler without being classified here.
SAMPLE_ARGS = {
    "copy": {"from": "a", "to": "t"},
    "rename": {"from": "a", "to": "t"},
    "derive_sum": {"parts": ["a", "b"], "to": "t"},
    "code_translate": {"from": "a", "to": "t", "table": {"X": "y"}},
    "assert_not_null": {"field": "a"},
}


def _python(rows, steps, target="t"):
    m = approved_mapping(target_artifact=target)
    plan = compile_mapping(m, steps)
    run = run_conversion(rows, plan, m, source_snapshot="s",
                         domain_pack_version="p", engine_version="e",
                         provenance_of=prov)
    return run


def _sqlite(rows, columns, steps, target="t"):
    m = approved_mapping(target_artifact=target)
    sql = compile_mapping_to_sql(m, steps, source_table="src", dialect="sqlite")
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE src (" + ",".join(f'"{c}"' for c in columns) + ")")
    for r in rows:
        db.execute("INSERT INTO src VALUES (" + ",".join("?" * len(columns)) + ")",
                   [r.get(c) for c in columns])
    return db.execute(sql).fetchall()


@pytest.mark.parametrize("op", ["copy", "rename"])
def test_executed_copy_and_rename_match_python(op):
    rows = [{"_id": 1, "a": 5}, {"_id": 2, "a": None}, {"_id": 3, "a": "x"},
            {"_id": 4, "a": 2.5}, {"_id": 5, "a": 0}, {"_id": 6, "a": ""}]
    steps = [PlanStep(op, {"from": "a", "to": "t"})]
    run = _python(rows, steps)
    assert run.converted == len(rows) and run.rejected == 0
    assert [(o["t"],) for o in run.outputs] == _sqlite(rows, ["_id", "a"], steps)


def test_every_op_is_classified_and_uncovered_ops_are_refused():
    """No op may be lowered to SQL without an executed equivalence test.

    New ops fail this test until they are classified, forcing the author to
    either refuse the lowering or add a differential test above."""
    assert set(SAMPLE_ARGS) == set(_REQUIRED_ARGS), \
        "new compiler op: add it to SAMPLE_ARGS and decide lowering vs refusal"
    m = approved_mapping(target_artifact="t")
    for op, args in SAMPLE_ARGS.items():
        step = PlanStep(op, args)
        if op in DIFFERENTIAL_COVERED:
            compile_mapping_to_sql(m, [step], source_table="src")   # must lower
        else:
            with pytest.raises(CompilationError, match="no SQL lowering"):
                compile_mapping_to_sql(m, [step], source_table="src")


def test_derive_sum_diverges_between_python_and_sql():
    """Why derive_sum is refused: execute the SELECT a naive lowering emits
    (`("a" + "b")`) next to the Python backend on the same rows."""
    data = [(1, 2), (None, 2), ("abc", 2), ("100", "50"), (1.5, None)]
    rows = [{"_id": i, "a": a, "b": b} for i, (a, b) in enumerate(data)]

    run = _python(rows, [PlanStep("derive_sum", {"parts": ["a", "b"], "to": "t"})])
    assert (run.converted, run.rejected) == (2, 3)          # 1+2 and "100"+"50"

    db = sqlite3.connect(":memory:")
    db.execute('CREATE TABLE src ("a","b")')
    db.executemany("INSERT INTO src VALUES (?,?)", data)
    sql_out = [r[0] for r in db.execute('SELECT ("a" + "b") FROM src')]

    assert sql_out[1] is None        # NULL component: Python rejects, SQL emits NULL
    assert sql_out[2] == 2           # "abc" + 2: Python rejects, SQL emits a wrong value
    assert sql_out[4] is None        # NULL component again
    # SQL produced a row for all five inputs; Python refused three of them.
    assert len(sql_out) == len(data) and run.rejected == 3


def test_derive_sum_lowering_is_refused():
    m = approved_mapping(target_artifact="t")
    with pytest.raises(CompilationError, match="no SQL lowering for derive_sum"):
        compile_mapping_to_sql(
            m, [PlanStep("derive_sum", {"parts": ["a", "b"], "to": "t"})],
            source_table="src")
