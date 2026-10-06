from sematik.identity import IdentityRegistry


def test_register_and_resolve():
    reg = IdentityRegistry()
    cid = reg.register("LDB", "APN:001-002")
    assert reg.resolve_exact("LDB", "APN:001-002") == cid


def test_explicit_probabilistic_is_recorded():
    reg = IdentityRegistry()
    cid = reg.register("LDB", "ACCT:55", strategy="probabilistic",
                       confidence=0.88, rationale=["name+address overlap"])
    d = reg.lineage(cid)[0]
    assert d.strategy == "probabilistic" and d.confidence == 0.88


def test_repeat_registration_is_idempotent():
    import pytest
    from sematik.identity import IdentityConflict
    reg = IdentityRegistry()
    cid = reg.register("LDB", "APN:001")
    assert reg.register("LDB", "APN:001") == cid
    assert reg.register("LDB", "APN:001", canonical_id=cid) == cid
    assert len(reg.lineage(cid)) == 1
    with pytest.raises(IdentityConflict):
        reg.register("LDB", "APN:001", canonical_id="id_other")


def test_reassignment_is_governed_and_keeps_history():
    import pytest
    from sematik.identity import IdentityConflict
    reg = IdentityRegistry()
    old = reg.register("LDB", "APN:001")
    with pytest.raises(ValueError, match="reason"):
        reg.reassign("LDB", "APN:001", "id_new", reason="  ")
    new = reg.reassign("LDB", "APN:001", "id_new", reason="deed review",
                       actor="op")
    assert new == "id_new"
    assert reg.resolve_exact("LDB", "APN:001") == "id_new"
    assert reg.lineage(old) != []
    assert "deed review" in reg.lineage("id_new")[0].rationale[0]
    with pytest.raises(IdentityConflict):
        reg.reassign("LDB", "APN:missing", "id_x", reason="r")


def test_non_finite_confidence_rejected():
    import pytest
    reg = IdentityRegistry()
    for bad in (float("nan"), float("inf"), -0.1, 1.1, "high"):
        with pytest.raises(ValueError):
            reg.register("LDB", "K", confidence=bad)
    with pytest.raises(ValueError):
        reg.reassign("LDB", "K", "id_x", reason="r", confidence=float("nan"))
