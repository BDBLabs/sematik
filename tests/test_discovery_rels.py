import pytest
from sematik.discovery import candidate_relationships
from sematik.model import Confidence, SemanticHypothesis


def test_detects_candidate_fk_like_column():
    # parcels.owner_id ⊆ owners.id → candidate relationship
    tables = {
        "parcels": [{"id": "p1", "owner_id": "o1"}, {"id": "p2", "owner_id": "o2"}, {"id": "p3", "owner_id": "o3"}],
        "owners": [{"id": "o1"}, {"id": "o2"}, {"id": "o3"}, {"id": "o4"}],
    }
    rels = candidate_relationships(tables)
    assert any(r["from"][1] == "owner_id" and r["to"][1] == "id" and r["overlap"] == 1.0 for r in rels)


def test_confidence_is_uncalibrated_confidence_object():
    """candidate_relationships emits Confidence, not a bare float (#36)."""
    tables = {
        "parcels": [{"id": "p1", "owner_id": "o1"}, {"id": "p2", "owner_id": "o2"}, {"id": "p3", "owner_id": "o3"}],
        "owners": [{"id": "o1"}, {"id": "o2"}, {"id": "o3"}, {"id": "o4"}],
    }
    rels = candidate_relationships(tables)
    assert len(rels) == 1
    c = rels[0]["confidence"]
    assert isinstance(c, Confidence)
    assert not c.calibrated
    assert "evidence_basis" in rels[0]
    assert rels[0]["evidence_basis"]  # non-empty, stated basis


def test_candidate_relationship_has_evidence_basis():
    """Per #36: no numeric confidence without a stated basis."""
    tables = {
        "parcels": [{"id": "p1", "owner_id": "o1"}, {"id": "p2", "owner_id": "o2"}, {"id": "p3", "owner_id": "o3"}],
        "owners": [{"id": "o1"}, {"id": "o2"}, {"id": "o3"}, {"id": "o4"}],
    }
    rels = candidate_relationships(tables)
    assert all(r["evidence_basis"] for r in rels)


def test_ignores_coincidental_low_overlap():
    tables = {
        "a": [{"k": "x1"}, {"k": "x2"}],
        "b": [{"k": "y1"}, {"k": "y2"}],
    }
    assert candidate_relationships(tables) == []


def test_ignores_low_cardinality_spurious_matches():
    """Boolean columns with trivial overlap must not produce FK candidates (#37)."""
    tables = {
        "t1": [{"flag": True, "id": "r1"}, {"flag": False, "id": "r2"}],
        "t2": [{"active": True, "id": "s1"}, {"active": False, "id": "s2"}],
    }
    # Both columns have 2 distinct values — below min_cardinality (default 3)
    assert candidate_relationships(tables) == []


def test_high_cardinality_match_still_detected():
    """With enough distinct values, real candidates are still found (#37)."""
    tables = {
        "parent": [{"id": f"p{i}"} for i in range(10)],
        "child": [{"parent_id": f"p{i}"} for i in range(10)],
    }
    rels = candidate_relationships(tables)
    # parent.id ⊆ child.parent_id → relationship from parent.id to child.parent_id
    assert any(r["from"][1] == "id" and r["to"][1] == "parent_id" for r in rels)


def test_min_cardinality_parameter_respected():
    """Raising min_cardinality suppresses borderline candidates."""
    tables = {
        "parcels": [{"id": f"p{i}", "owner_id": f"o{i}"} for i in range(3)],
        "owners": [{"id": f"o{i}"} for i in range(3)],
    }
    # 3 distinct values — passes with default min_cardinality=3
    assert len(candidate_relationships(tables)) == 1
    # 10 distinct values required — now suppressed
    assert candidate_relationships(tables, min_cardinality=10) == []


# ---- #36: SemanticHypothesis requires evidence_basis for uncalibrated confidence

def test_uncalibrated_hypothesis_requires_evidence_basis():
    """A Confidence with calibrated=False must carry evidence_basis (#36 F-06)."""
    c = Confidence.from_evidence_strength("moderate", ("signal",))
    with pytest.raises(ValueError, match="evidence_basis"):
        SemanticHypothesis(candidate_meaning="x", concept="c",
                           confidence=c, evidence_basis="")  # uncalibrated + empty


def test_calibrated_hypothesis_allows_empty_evidence_basis():
    """Calibrated (human-asserted) confidence does not require evidence_basis."""
    c = Confidence(0.9, calibrated=True)
    h = SemanticHypothesis(candidate_meaning="x", concept="c",
                           confidence=c, evidence_basis="")
    assert h.confidence.calibrated
