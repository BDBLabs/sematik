from sematik.mapping import Mapping
from sematik.model import Confidence
from sematik.semantic_diff import semantic_diff


def _m():
    m = Mapping(source_artifact="LDB.PARCEL.OWNER_STAT",
                canonical_concept="Ownership.party_kind", target_artifact="owner_kind",
                confidence=Confidence(0.8), rule_refs=["R1"], approved_by="t")
    m.add_level(1, "physical", "OWNER_STAT → raw")
    m.add_level(2, "semantic", "OWNER_STAT → owner status")
    return m


def test_meaning_change_detected():
    old = _m()
    new = _m()
    new.levels[1] = type(new.levels[1])(level=2, kind="semantic",
                                        statement="OWNER_STAT → responsible party")
    d = semantic_diff(old, new)
    assert d["meaning_changed"] and "responsible party" in d["changes"][0]


def test_no_meaning_change_no_diff():
    assert semantic_diff(_m(), _m())["meaning_changed"] is False


def test_context_change_is_meaning_change():
    new = _m()
    new.levels.append(type(new.levels[0])(level=4, kind="context",
                                          statement="roll scope",
                                          context={"roll_type": "REGULAR"}))
    newer = _m()
    newer.levels.append(type(newer.levels[0])(level=4, kind="context",
                                              statement="roll scope",
                                              context={"roll_type": "SUPPLEMENTAL"}))
    d = semantic_diff(new, newer)
    assert d["meaning_changed"] and any("context" in c for c in d["changes"])


def test_domain_pack_change_is_meaning_change():
    old = _m()
    new = _m()
    new.domain_pack = "cpasf@0.2.0"
    d = semantic_diff(old, new)
    assert d["meaning_changed"] and any("domain pack" in c for c in d["changes"])


def test_added_level_is_meaning_change():
    old = _m()
    new = _m()
    new.add_level(4, "context", "roll scope", roll_type="REGULAR")
    d = semantic_diff(old, new)
    assert d["meaning_changed"] and any("added" in c for c in d["changes"])
