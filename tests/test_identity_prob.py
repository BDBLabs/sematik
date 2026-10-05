from sematik.identity import probabilistic_match


def test_probabilistic_match_enforces_threshold():
    a = {"owner": "Smith John", "apn": "001-002", "city": "San Diego"}
    b = {"owner": "Smith  John", "apn": "001-002", "city": "San Diego"}
    matched, conf, misses = probabilistic_match(a, b, ["owner", "apn", "city"])
    assert matched and conf == 1.0


def test_probabilistic_match_rejects_when_keys_differ():
    a = {"owner": "Smith John", "apn": "001-002", "city": "San Diego"}
    c = {"owner": "Jones Mary", "apn": "999-999", "city": "El Cajon"}
    matched, conf, misses = probabilistic_match(a, c, ["owner", "apn", "city"])
    assert not matched and misses == ["owner", "apn", "city"]
