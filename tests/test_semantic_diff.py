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
