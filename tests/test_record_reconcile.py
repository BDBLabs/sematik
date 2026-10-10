from sematik.reconcile import reconcile_records


def _rec(src, outputs, pairs=(("LNDVAL", "total_assessed"),)):
    return reconcile_records(src, outputs, source_key="APN", target_key="apn",
                             numeric_pairs=list(pairs))


def test_record_reconcile_detects_misattached_value():
    src = [{"APN": "001", "LNDVAL": 100, "AV_IMP": 50},
           {"APN": "002", "LNDVAL": 200, "AV_IMP": 50}]
    # Wrong: total_assessed for 001 uses 002's components
    outputs = [{"apn": "001", "total_assessed": 250.0}, {"apn": "002", "total_assessed": 250.0}]
    r = reconcile_records(src, outputs, source_key="APN", target_key="apn",
                          numeric_pairs=[("LNDVAL", "total_assessed")])
    # 001 expected 100, got 250 → mismatch; 002 expected 200, got 250 → mismatch
    assert len(r["mismatches"]) == 2 and r["balanced"] is False


def test_record_reconcile_passes_when_derivation_holds():
    src = [{"APN": "001", "LNDVAL": 100.0 + 50.0}]
    outputs = [{"apn": "001", "total_assessed": 150.0}]
    r = reconcile_records(src, outputs, source_key="APN", target_key="apn",
                          numeric_pairs=[("LNDVAL", "total_assessed")])
    assert r["balanced"] and r["checked"] == 1


def test_missing_target_amount_is_not_balanced():
    r = _rec([{"APN": "001", "LNDVAL": 100}],
             [{"apn": "001"}])
    assert r["balanced"] is False
    assert r["mismatches"][0]["kind"] == "missing_target"


def test_nan_target_amount_is_not_balanced():
    r = _rec([{"APN": "001", "LNDVAL": 100}],
             [{"apn": "001", "total_assessed": float("nan")}])
    assert r["balanced"] is False
    assert r["mismatches"][0]["kind"] == "invalid_target"


def test_non_numeric_target_is_not_balanced():
    r = _rec([{"APN": "001", "LNDVAL": 100}],
             [{"apn": "001", "total_assessed": "one hundred"}])
    assert r["balanced"] is False
    assert r["mismatches"][0]["kind"] == "invalid_target"


def test_missing_source_value_is_not_balanced():
    r = _rec([{"APN": "001"}],
             [{"apn": "001", "total_assessed": 100.0}])
    assert r["balanced"] is False
    assert r["mismatches"][0]["kind"] == "unsupported_source"


def test_output_without_source_row_is_unmatched():
    r = _rec([{"APN": "001", "LNDVAL": 100}],
             [{"apn": "001", "total_assessed": 100.0},
              {"apn": "999", "total_assessed": 1.0}])
    assert r["balanced"] is False
    assert r["unmatched"] == ["999"]
    assert r["checked"] == 1


def test_duplicate_keys_are_not_balanced():
    r = _rec([{"APN": "001", "LNDVAL": 100}],
             [{"apn": "001", "total_assessed": 100.0},
              {"apn": "001", "total_assessed": 100.0}])
    assert r["balanced"] is False
    assert r["duplicates"] == ["001"]


# ---- #31 regression: Decimal totals from exact-numeric derive_sum -------------

def test_decimal_target_is_valid_amount():
    """A Decimal total (e.g. from derive_sum preserving Decimal semantics)
    must not be falsely flagged as an invalid_target (#31 follow-up)."""
    from decimal import Decimal
    r = _rec([{"APN": "001", "LNDVAL": 100}],
             [{"apn": "001", "total_assessed": Decimal("100.0")}])
    assert r["balanced"] is True
    assert r["mismatches"] == []


def test_decimal_source_and_target_match():
    """Both source total and target are Decimal — derivation must hold."""
    from decimal import Decimal
    src = [{"APN": "001", "LNDVAL": Decimal("150.0")}]
    outputs = [{"apn": "001", "total_assessed": Decimal("150.0")}]
    r = reconcile_records(src, outputs, source_key="APN", target_key="apn",
                          numeric_pairs=[("LNDVAL", "total_assessed")])
    assert r["balanced"] is True
    assert r["checked"] == 1
