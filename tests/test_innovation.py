from sematik.domain_pack import CodeSet, DomainPack
from sematik.entropy import concept_entropy, semantic_entropy
from sematik.entropy import semantic_entropy_flagged, UncalibratedConfidence
from sematik.golden import run_golden_records
from sematik.model import Confidence
from sematik.model import SemanticHypothesis
from sematik.compiler import PlanStep, compile_mapping
from sematik.mapping import Mapping
from sematik.discovery import hypotheses_for_column, profile_column
from sematik.record_confidence import record_confidence
from helpers import approved_mapping

import pytest


def _hyp(concept, conf, records=10):
    """Calibrated test hypothesis (calibrated=True is the default)."""
    return SemanticHypothesis(candidate_meaning="x", concept=concept,
                              confidence=Confidence(conf, calibrated=True),
                              affected_records=records)


def _uncalibrated(concept, conf, records=10):
    """Uncalibrated hypothesis (as produced by discovery heuristics)."""
    return SemanticHypothesis(candidate_meaning="x", concept=concept,
                              confidence=Confidence.from_evidence_strength(
                                  "moderate", ("test",)),
                              affected_records=records)


def test_entropy_zero_when_certain():
    assert concept_entropy([_hyp("c", 0.99)]) < 0.2


def test_entropy_counts_uniform_ambiguity():
    hs = [_hyp("c", 0.5, 100), _hyp("c", 0.5, 100)]
    assert concept_entropy(hs) > 0.9   # two equally-likely meanings


def test_semantic_entropy_weighted():
    hs = [_hyp("a", 0.99, 900), _hyp("b", 0.5, 100), _hyp("b", 0.5, 100)]
    s = semantic_entropy(hs)
    assert 0.0 < s < 0.5   # dominated by the well-understood concept


# ---- #36: entropy refuses uncalibrated confidences ---------------------------

def test_concept_entropy_refuses_uncalibrated():
    """Uncalibrated heuristic confidences must not feed entropy — they are
    ordinal strength, not calibrated probabilities (#36)."""
    with pytest.raises(UncalibratedConfidence, match="uncalibrated"):
        concept_entropy([_hyp("c", 0.99), _uncalibrated("c", 0.5)])


def test_semantic_entropy_refuses_uncalibrated():
    with pytest.raises(UncalibratedConfidence, match="uncalibrated"):
        semantic_entropy([_hyp("a", 0.99, 900), _uncalibrated("b", 0.5, 100)])


def test_semantic_entropy_flagged_returns_warnings():
    """The flagged variant never raises — it returns a score plus warnings
    for uncalibrated inputs (#36)."""
    hs = [_hyp("a", 0.99, 900), _uncalibrated("b", 0.5, 100)]
    score, warnings = semantic_entropy_flagged(hs)
    assert 0.0 <= score <= 1.0
    assert len(warnings) == 1
    assert "uncalibrated" in warnings[0]


def test_discovery_hypotheses_are_uncalibrated():
    """Hypotheses from hypotheses_for_column() carry calibrated=False and a
    stated evidence_basis (#36)."""
    profile = profile_column([1, 2, 3, 4, 5])
    hyps = hypotheses_for_column("test_col", profile)
    assert all(not h.confidence.calibrated for h in hyps)
    assert all(h.evidence_basis for h in hyps)


def test_from_evidence_strength_mapping():
    """Ordinal strengths map to expected midpoints, all uncalibrated (#36)."""
    weak = Confidence.from_evidence_strength("weak", ("driver",))
    moderate = Confidence.from_evidence_strength("moderate", ("driver",))
    strong = Confidence.from_evidence_strength("strong", ("driver",))
    assert weak.overall == 0.33
    assert moderate.overall == 0.5
    assert strong.overall == 0.75
    assert not weak.calibrated and not moderate.calibrated and not strong.calibrated
    with pytest.raises(ValueError, match="evidence strength"):
        Confidence.from_evidence_strength("bogus", ())


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
    mapping = approved_mapping()
    plan = compile_mapping(mapping, [PlanStep("copy", {"from": "a", "to": "t"})])
    golden = [{"name": "g1", "input": {"a": 1, "_id": "1"}, "expected": {"t": 1}}]
    assert run_golden_records(plan, golden)["ok"]
    bad = [{"name": "g2", "input": {"a": 1, "_id": "1"}, "expected": {"t": 2}}]
    assert not run_golden_records(plan, bad)["ok"]
