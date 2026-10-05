from sematik.domain_pack import CodeSet, DomainPack
from sematik.entropy import concept_entropy, semantic_entropy
from sematik.golden import run_golden_records
from sematik.model import Confidence
from sematik.model import SemanticHypothesis
from sematik.compiler import PlanStep, compile_mapping
from sematik.mapping import Mapping
from sematik.record_confidence import record_confidence


def _hyp(concept, conf, records=10):
    return SemanticHypothesis(candidate_meaning="x", concept=concept,
                              confidence=Confidence(conf), affected_records=records)


def test_entropy_zero_when_certain():
    assert concept_entropy([_hyp("c", 0.99)]) < 0.2


def test_entropy_counts_uniform_ambiguity():
    hs = [_hyp("c", 0.5, 100), _hyp("c", 0.5, 100)]
    assert concept_entropy(hs) > 0.9   # two equally-likely meanings


def test_semantic_entropy_weighted():
    hs = [_hyp("a", 0.99, 900), _hyp("b", 0.5, 100), _hyp("b", 0.5, 100)]
    s = semantic_entropy(hs)
    assert 0.0 < s < 0.5   # dominated by the well-understood concept


def test_domain_pack_translation_and_loss():
    pack = DomainPack(name="cpasf", version="0.1.0", code_sets={
        "transfer": CodeSet("transfer", {"REG": "regular", "PT": "partial"}, discarded={"TMP", "TEST"}),
    })
    assert pack.translate("transfer", "REG") == "regular"
    report = pack.loss_report("transfer")
    assert report["discarded"] == ["TEST", "TMP"]


def test_record_level_outlier_detection():
    rows = [{"STAT": "A", "T": "x"} for _ in range(200)] + [{"STAT": "Z4", "T": "q"}]
    scored = record_confidence(rows, ["STAT", "T"])
    outliers = [s for s in scored if s["outlier"]]
    assert len(outliers) == 1 and outliers[0]["record"]["STAT"] == "Z4"


def test_golden_records_pass_and_fail():
    mapping = Mapping(source_artifact="s", canonical_concept="c",
                      target_artifact="t", approved_by="t",
                      confidence=Confidence(0.9))
    mapping.add_level(1, "physical", "x")
    plan = compile_mapping(mapping, [PlanStep("copy", {"from": "a", "to": "t"})])
    golden = [{"name": "g1", "input": {"a": 1, "_id": "1"}, "expected": {"t": 1}}]
    assert run_golden_records(plan, golden)["ok"]
    bad = [{"name": "g2", "input": {"a": 1, "_id": "1"}, "expected": {"t": 2}}]
    assert not run_golden_records(plan, bad)["ok"]
