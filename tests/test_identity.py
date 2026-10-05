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
