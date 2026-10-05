from sematik.reconcile import reconcile_records


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
