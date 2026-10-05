from sematik.discovery import candidate_relationships


def test_detects_candidate_fk_like_column():
    # parcels.owner_id ⊆ owners.id → candidate relationship
    tables = {
        "parcels": [{"id": "p1", "owner_id": "o1"}, {"id": "p2", "owner_id": "o2"}, {"id": "p3", "owner_id": "o3"}],
        "owners": [{"id": "o1"}, {"id": "o2"}, {"id": "o3"}, {"id": "o4"}],
    }
    rels = candidate_relationships(tables)
    assert any(r["from"][1] == "owner_id" and r["to"][1] == "id" and r["overlap"] == 1.0 for r in rels)


def test_ignores_coincidental_low_overlap():
    tables = {
        "a": [{"k": "x1"}, {"k": "x2"}],
        "b": [{"k": "y1"}, {"k": "y2"}],
    }
    assert candidate_relationships(tables) == []
