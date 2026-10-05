from sematik.compiler import PlanStep, compile_mapping
from sematik.mapping import Mapping
from sematik.model import Confidence
from sematik.runner import run_conversion


def _plan():
    m = Mapping(source_artifact="s", canonical_concept="c", target_artifact="t",
                approved_by="t", confidence=Confidence(0.9))
    m.add_level(1, "physical", "x")
    return m, compile_mapping(m, [PlanStep("copy", {"from": "a", "to": "t"})])


def test_golden_results_recorded_on_run():
    mapping, plan = _plan()
    golden = [{"name": "g1", "input": {"a": 1, "_id": "1"}, "expected": {"t": 1}}]
    run = run_conversion([{"a": 2, "_id": "x"}], plan, mapping,
                         source_snapshot="s", domain_pack_version="p", engine_version="e",
                         provenance_of=lambda r: None, golden=golden)
    assert run.golden is not None and run.golden["ok"]


def test_golden_failure_changes_manifest_hash():
    mapping, plan = _plan()
    good = [{"name": "g", "input": {"a": 1, "_id": "1"}, "expected": {"t": 1}}]
    bad = [{"name": "g", "input": {"a": 1, "_id": "1"}, "expected": {"t": 999}}]
    r1 = run_conversion([{"a": 1, "_id": "x"}], plan, mapping,
                        source_snapshot="s", domain_pack_version="p", engine_version="e",
                        provenance_of=lambda r: None, golden=good)
    r2 = run_conversion([{"a": 1, "_id": "x"}], plan, mapping,
                        source_snapshot="s", domain_pack_version="p", engine_version="e",
                        provenance_of=lambda r: None, golden=bad)
    assert r1.golden["ok"] and not r2.golden["ok"]
    assert r1.manifest_hash() != r2.manifest_hash()
