from helpers import approved_mapping, prov
from sematik.compiler import PlanStep, compile_mapping
from sematik.runner import run_conversion


def _plan():
    m = approved_mapping()
    return m, compile_mapping(m, [PlanStep("copy", {"from": "a", "to": "t"})])


def test_golden_results_recorded_on_run():
    mapping, plan = _plan()
    golden = [{"name": "g1", "input": {"a": 1, "_id": "1"}, "expected": {"t": 1}}]
    run = run_conversion([{"a": 2, "_id": "x"}], plan, mapping,
                         source_snapshot="s", domain_pack_version="p", engine_version="e",
                         provenance_of=prov, golden=golden)
    assert run.golden is not None and run.golden["ok"]


def test_golden_failure_changes_manifest_hash():
    mapping, plan = _plan()
    good = [{"name": "g", "input": {"a": 1, "_id": "1"}, "expected": {"t": 1}}]
    bad = [{"name": "g", "input": {"a": 1, "_id": "1"}, "expected": {"t": 999}}]
    r1 = run_conversion([{"a": 1, "_id": "x"}], plan, mapping,
                        source_snapshot="s", domain_pack_version="p", engine_version="e",
                        provenance_of=prov, golden=good)
    r2 = run_conversion([{"a": 1, "_id": "x"}], plan, mapping,
                        source_snapshot="s", domain_pack_version="p", engine_version="e",
                        provenance_of=prov, golden=bad)
    assert r1.golden["ok"] and not r2.golden["ok"]
    assert r1.manifest_hash() != r2.manifest_hash()


def test_require_golden_blocks_failing_plan_before_conversion():
    import pytest
    from sematik.compiler import CompilationError
    mapping, plan = _plan()
    bad = [{"name": "g", "input": {"a": 1, "_id": "1"}, "expected": {"t": 999}}]
    with pytest.raises(CompilationError, match="golden regression failed"):
        run_conversion([{"a": 1, "_id": "x"}], plan, mapping,
                       source_snapshot="s", domain_pack_version="p", engine_version="e",
                       provenance_of=prov, golden=bad, require_golden=True)


def test_require_golden_rejects_missing_evidence():
    import pytest
    from sematik.compiler import CompilationError
    mapping, plan = _plan()
    for missing in (None, []):
        with pytest.raises(CompilationError, match="no golden records"):
            run_conversion([{"a": 1, "_id": "x"}], plan, mapping,
                           source_snapshot="s", domain_pack_version="p",
                           engine_version="e", provenance_of=prov,
                           golden=missing, require_golden=True)


def test_require_golden_passes_and_records_evidence():
    mapping, plan = _plan()
    good = [{"name": "g", "input": {"a": 1, "_id": "1"}, "expected": {"t": 1}}]
    run = run_conversion([{"a": 1, "_id": "x"}], plan, mapping,
                         source_snapshot="s", domain_pack_version="p", engine_version="e",
                         provenance_of=prov, golden=good, require_golden=True)
    assert run.converted == 1 and run.golden["ok"]
