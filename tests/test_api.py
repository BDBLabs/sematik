"""Tests for the FastAPI backend wrapping the sematik engine.

Uses fastapi.testclient.TestClient (in-process, no network).
Covers the demo lifecycle end-to-end: fixture load -> profile -> hypotheses ->
compile (Python + SQL) -> execute -> reconcile -> entropy -> manifest."""

import json
import pathlib

import pytest
from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures"


@pytest.fixture(scope="module")
def rows():
    return json.loads((FIXTURE_DIR / "legacy_parcels.json").read_text())["rows"]


# ---------------------------------------------------------------------------
# Health + fixtures
# ---------------------------------------------------------------------------

def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_fixture_legacy_parcels(rows):
    r = client.get("/api/v1/fixture/legacy_parcels")
    assert r.status_code == 200
    assert len(r.json()) == len(rows)


def test_fixture_demo_mapping():
    r = client.get("/api/v1/fixture/demo-mapping")
    assert r.status_code == 200
    m = r.json()
    assert m["canonical_concept"].startswith("Assessment")
    assert len(m["levels"]) == 7
    assert m["confidence"]["overall"] == 0.9
    assert m["confidence"]["calibrated"] is True


def test_fixture_demo_steps():
    r = client.get("/api/v1/fixture/demo-steps")
    assert r.status_code == 200
    assert len(r.json()) == 3
    assert r.json()[0]["op"] == "derive_sum"


# ---------------------------------------------------------------------------
# Discovery plane
# ---------------------------------------------------------------------------

def test_profile_column(rows):
    apn_values = [r["APN"] for r in rows]
    r = client.post("/api/v1/profile", json={"name": "APN", "values": apn_values})
    assert r.status_code == 200
    p = r.json()
    assert p["count"] == 4
    assert p["distinct"] == 4
    assert p["distinct_ratio"] == 1.0  # all unique


def test_hypotheses_show_uncalibrated(rows):
    apn_values = [r["APN"] for r in rows]
    r = client.post("/api/v1/hypotheses",
                    json={"name": "APN", "values": apn_values})
    assert r.status_code == 200
    hyps = r.json()
    assert len(hyps) >= 1
    # Discovery hypotheses are uncalibrated (ordinal evidence strength)
    assert all(not h["confidence"]["calibrated"] for h in hyps)
    # Every hypothesis must carry a stated basis (#36)
    assert all(h["evidence_basis"] for h in hyps)


def test_candidates_suppress_low_cardinality():
    """Boolean columns with trivial overlap must not produce candidates (#37)."""
    tables = {
        "t1": [{"flag": True}, {"flag": False}],
        "t2": [{"active": True}, {"active": False}],
    }
    r = client.post("/api/v1/candidates", json={"tables": tables})
    assert r.status_code == 200
    assert r.json() == []


def test_candidates_detect_real_fk():
    tables = {
        "parent": [{"id": f"p{i}"} for i in range(10)],
        "child": [{"parent_id": f"p{i}"} for i in range(10)],
    }
    r = client.post("/api/v1/candidates", json={"tables": tables})
    assert r.status_code == 200
    rels = r.json()
    assert len(rels) == 1
    c = rels[0]["confidence"]
    assert isinstance(c, dict)
    assert c["calibrated"] is False  # uncalibrated heuristic


# ---------------------------------------------------------------------------
# Compilation plane
# ---------------------------------------------------------------------------

def test_mapping_digest():
    r = client.get("/api/v1/fixture/demo-mapping")
    m = r.json()
    # Verify this is a valid, approved mapping
    r2 = client.post("/api/v1/mapping/digest", json=m)
    assert r2.status_code == 200
    info = r2.json()
    assert info["complete"] is True
    assert info["approved"] is True
    assert info["approval_problems"] == []


def test_compile_python_plan():
    m = client.get("/api/v1/fixture/demo-mapping").json()
    steps = client.get("/api/v1/fixture/demo-steps").json()
    # Remove code_translate (refused at runtime for UNK9); test copy + derive_sum
    safe_steps = [s for s in steps if s["op"] in ("copy", "derive_sum")]
    r = client.post("/api/v1/compile", json={"mapping": m, "steps": safe_steps})
    assert r.status_code == 200
    info = r.json()
    assert info["target_artifact"] == "total_assessed"
    assert len(info["steps"]) == 2


def test_compile_sql():
    m = client.get("/api/v1/fixture/demo-mapping").json()
    steps = client.get("/api/v1/fixture/demo-steps").json()
    safe_steps = [s for s in steps if s["op"] in ("copy", "derive_sum")]
    r = client.post("/api/v1/compile-sql",
                    json={"mapping": m, "steps": safe_steps,
                          "source_table": "legacy_parcel"})
    assert r.status_code == 200
    sql = r.json()["sql"]
    assert '"total_assessed"' in sql
    assert '"APN" AS "apn"' in sql
    assert 'FROM "legacy_parcel"' in sql


def test_compile_sql_refuses_code_translate():
    """SQL lowering must refuse code_translate (fail-closed, §68)."""
    m = client.get("/api/v1/fixture/demo-mapping").json()
    ct_step = {"op": "code_translate",
               "args": {"from": "XFER", "to": "transfer_kind",
                        "table": {"REG": "regular", "PT": "partial"}}}
    r = client.post("/api/v1/compile-sql",
                    json={"mapping": m, "steps": [ct_step], "source_table": "src"})
    assert r.status_code == 400


def test_compile_unapproved_mapping_rejected():
    """Unapproved mappings refuse to compile (#24)."""
    m = client.get("/api/v1/fixture/demo-mapping").json()
    m["approved_by"] = ""  # strip approval
    r = client.post("/api/v1/compile",
                    json={"mapping": m, "steps": [{"op": "copy", "args": {"from": "a", "to": "b"}}]})
    assert r.status_code == 400
    assert "approved" in r.json()["detail"].lower()


def test_compile_sql_rejects_unknown_dialect():
    m = client.get("/api/v1/fixture/demo-mapping").json()
    r = client.post("/api/v1/compile-sql",
                    json={"mapping": m, "steps": [{"op": "copy", "args": {"from": "a", "to": "b"}}],
                          "source_table": "t", "dialect": "oracle"})
    assert r.status_code == 400


def test_sql_comment_strips_newlines():
    """SQL injection via newline in mapping.id must be blocked (#30)."""
    m = client.get("/api/v1/fixture/demo-mapping").json()
    m["id"] = "evil\nDROP TABLE users;"  # override the default UUID id
    r = client.post("/api/v1/compile-sql",
                    json={"mapping": m, "steps": [{"op": "copy", "args": {"from": "a", "to": "b"}}],
                          "source_table": "t"})
    assert r.status_code == 200
    sql = r.json()["sql"]
    for line in sql.split("\n"):
        assert not line.strip().startswith("DROP"), f"SQL injection! line: {line!r}"


# ---------------------------------------------------------------------------
# Execution plane
# ---------------------------------------------------------------------------

def test_execute_full_lifecycle(rows):
    """End-to-end: the demo mapping + steps should produce 3 converted,
    1 rejected (XFER=UNK9) — matching demo.py output."""
    m = client.get("/api/v1/fixture/demo-mapping").json()
    steps = client.get("/api/v1/fixture/demo-steps").json()
    r = client.post("/api/v1/execute", json={
        "mapping": m,
        "steps": steps,
        "rows": rows,
    })
    assert r.status_code == 200
    result = r.json()
    assert result["converted"] == 3
    assert result["rejected"] == 1
    assert result["total"] == 4
    assert len(result["exceptions"]) == 1
    assert result["exceptions"][0]["phase"] == "execution"
    # Manifest hash must be present and stable
    assert len(result["manifest_hash"]) == 64


def test_execute_preserves_int_totals(rows):
    """derive_sum must preserve int types (issue #31), not coerce to float."""
    m = client.get("/api/v1/fixture/demo-mapping").json()
    steps = client.get("/api/v1/fixture/demo-steps").json()
    r = client.post("/api/v1/execute", json={"mapping": m, "steps": steps, "rows": rows})
    assert r.status_code == 200
    # total_assessed in first output should be 200000 (int), not 200000.0
    for out in r.json()["outputs"]:
        if "total_assessed" in out:
            assert isinstance(out["total_assessed"], int), \
                f"expected int, got {type(out['total_assessed'])}"
            assert out["total_assessed"] == 200000
            break


def test_execute_golden_gate_blocks_failing_plan(rows):
    """A failing golden record must block execution before any conversion (§61)."""
    m = client.get("/api/v1/fixture/demo-mapping").json()
    bad_golden = [{"name": "g2", "input": {"a": 1, "_id": "1"},
                   "expected": {"t": 2}}]
    r = client.post("/api/v1/execute", json={
        "mapping": m,
        "steps": [{"op": "copy", "args": {"from": "APN", "to": "apn"}}],
        "rows": rows[:1],
        "golden": bad_golden,
        "require_golden": True,
    })
    assert r.status_code == 400
    assert "golden" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Reconciliation plane
# ---------------------------------------------------------------------------

def test_population_reconciliation(rows):
    m = client.get("/api/v1/fixture/demo-mapping").json()
    steps = client.get("/api/v1/fixture/demo-steps").json()
    exec_r = client.post("/api/v1/execute", json={"mapping": m, "steps": steps, "rows": rows})
    outputs = exec_r.json()["outputs"]
    r = client.post("/api/v1/reconcile/population",
                    json={"rows": rows, "outputs": outputs,
                          "source_key": "APN", "target_key": "apn"})
    assert r.status_code == 200
    assert r.json()["balanced"] is False  # APN ≠ apn values


# ---------------------------------------------------------------------------
# Entropy plane — §76
# ---------------------------------------------------------------------------

def test_concept_entropy_calibrated():
    """Calibrated hypotheses can compute entropy."""
    hyps = [
        {"candidate_meaning": "meaning A", "concept": "c",
         "confidence": {"overall": 0.99, "calibrated": True}},
        {"candidate_meaning": "meaning B", "concept": "c",
         "confidence": {"overall": 0.5, "calibrated": True}},
        {"candidate_meaning": "meaning C", "concept": "c",
         "confidence": {"overall": 0.5, "calibrated": True}},
    ]
    r = client.post("/api/v1/entropy/concept", json=hyps)
    assert r.status_code == 200
    assert 0 < r.json()["entropy"] < 2


def test_concept_entropy_refuses_uncalibrated():
    """Uncalibrated hypotheses must be refused (§76/#36)."""
    hyps = [
        {"candidate_meaning": "meaning A", "concept": "c",
         "confidence": {"overall": 0.5, "calibrated": False}},
    ]
    r = client.post("/api/v1/entropy/concept", json=hyps)
    assert r.status_code == 422
    assert "uncalibrated" in r.json()["detail"].lower()


def test_semantic_entropy_flagged_never_raises():
    """The flagged variant returns a score + warning, never 422 (#36)."""
    hyps = [
        {"candidate_meaning": "a", "concept": "a",
         "confidence": {"overall": 0.99, "calibrated": True}},
        {"candidate_meaning": "b", "concept": "b",
         "confidence": {"overall": 0.5, "calibrated": False},
         "evidence_basis": "heuristic: test"},
    ]
    r = client.post("/api/v1/entropy/semantic-flagged", json=hyps)
    assert r.status_code == 200
    result = r.json()
    assert "entropy" in result
    assert len(result["warnings"]) == 1
    assert "uncalibrated" in result["warnings"][0]
