from sematik.cpasf_pack import cpasf_pack, CPASF_CONCEPTS


def test_pack_carries_vocabulary_and_codesets():
    pack = cpasf_pack()
    assert pack.name == "cpasf"
    assert "Assessment" in pack.canonical_concepts
    assert set(pack.code_sets) >= {"roll_type", "taxability_state", "transfer_kind", "ownership_state"}
    assert pack.translate("roll_type", "SUP") == "supplemental"


def test_unknown_code_is_rejected():
    pack = cpasf_pack()
    try:
        pack.translate("roll_type", "WTF")
        assert False, "expected KeyError"
    except KeyError:
        pass
