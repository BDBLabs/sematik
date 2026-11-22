"""Hybrid retrieval: rank fusion, abstention, and typed evidence emission."""

import ast
import pathlib

import pytest

from sematik.egress import DataClassification
from sematik.hybrid import (evidence_from_retrieval, reciprocal_rank_fusion, retrieve)
from sematik.investigation import (CompetingInterpretation, EvidenceAuthority,
                                   EvidenceMethod, EvidenceStance, InvestigationPacket)
from sematik.lexical import BM25Index, Glossary

DOCS = {
    "Transfer": "A change of ownership or other transfer event",
    "Appeal": "A contest of an assessed conclusion",
    "Exemption": "An exclusion reducing taxable value",
}
SOURCE = pathlib.Path(__file__).parent.parent / "src" / "sematik"


def test_rrf_scores_follow_the_formula():
    s = reciprocal_rank_fusion({"a": ["x", "y", "z"], "b": ["y", "z"]}, k=60)
    assert s["x"] == pytest.approx(1 / 61)
    assert s["y"] == pytest.approx(1 / 62 + 1 / 61)
    assert s["z"] == pytest.approx(1 / 63 + 1 / 62)
    with pytest.raises(ValueError):
        reciprocal_rank_fusion({"a": ["x"]}, k=0)


def test_lexical_only_retrieval_records_ranks_and_methods():
    r = retrieve("TRANSFER_EVENT", lexical=BM25Index(DOCS))
    assert not r.abstained and r.ranked_ids[0] == "Transfer"
    assert r.methods == ("lexical",) and r.methods_with_hits == ("lexical",)
    assert r.hits[0].ranks == {"lexical": 1} and r.hits[0].dense_score is None


def test_no_overlap_means_abstention_with_a_reason():
    r = retrieve("UI_THEME", lexical=BM25Index(DOCS))
    assert r.abstained and r.hits == () and "no retrieval method" in r.reason


def test_lexical_floor_forces_abstention():
    r = retrieve("TRANSFER_EVENT", lexical=BM25Index(DOCS), min_lexical_score=999.0)
    assert r.abstained


def test_dense_contributes_when_lexical_has_nothing():
    r = retrieve("ZZZ_QQQ", lexical=BM25Index(DOCS), dense_ranker=lambda q: [("Appeal", 0.8)],
                 dense_descriptor="fake/embed-1")
    assert not r.abstained and r.methods_with_hits == ("dense",)
    assert r.hits[0].doc_id == "Appeal" and r.hits[0].dense_score == 0.8


def test_fusion_rewards_agreement_between_methods():
    dense = lambda q: [("Exemption", 0.9), ("Transfer", 0.8)]
    r = retrieve("TRANSFER_EVENT", lexical=BM25Index(DOCS), dense_ranker=dense,
                 dense_descriptor="fake/embed-1")
    assert r.ranked_ids[0] == "Transfer"
    assert set(r.hits[0].ranks) == {"lexical", "dense"}
    assert r.hits[0].score > r.hits[1].score


def test_dense_floor_filters_and_both_empty_abstains():
    r = retrieve("UI_THEME", lexical=BM25Index(DOCS), min_dense_score=0.5,
                 dense_ranker=lambda q: [("Appeal", 0.2)], dense_descriptor="fake/embed-1")
    assert r.abstained and r.methods == ("lexical", "dense")


def test_dense_duplicates_are_ignored_and_order_is_deterministic():
    dense = lambda q: [("Appeal", 0.5), ("Appeal", 0.9), ("Exemption", 0.5)]
    r = retrieve("ZZZ", lexical=BM25Index(DOCS), dense_ranker=dense, dense_descriptor="fake/embed-1")
    assert r.ranked_ids == ("Appeal", "Exemption")


@pytest.mark.parametrize("bad", [[("Appeal", float("nan"))], [("Appeal", True)],
                                 [(1, 0.5)], [("Appeal", float("inf"))]])
def test_malformed_dense_output_is_rejected(bad):
    with pytest.raises(ValueError, match="dense ranker"):
        retrieve("ZZZ", lexical=BM25Index(DOCS), dense_ranker=lambda q: bad,
                 dense_descriptor="fake/embed-1")


def test_top_k_and_input_validation():
    assert len(retrieve("value change appeal", lexical=BM25Index(DOCS), top_k=1).hits) == 1
    with pytest.raises(ValueError):
        retrieve(" ", lexical=BM25Index(DOCS))
    with pytest.raises(ValueError):
        retrieve("x", lexical=BM25Index(DOCS), top_k=0)


def test_a_dense_ranker_without_a_descriptor_is_refused_so_evidence_stays_replayable():
    with pytest.raises(ValueError, match="dense_descriptor"):
        retrieve("ZZZ", lexical=BM25Index(DOCS), dense_ranker=lambda q: [("Appeal", 0.8)])


# ---- evidence emission -----------------------------------------------------

def _evidence(index=None, query="TRANSFER_EVENT", **kw):
    index = index or BM25Index(DOCS)
    result = retrieve(query, lexical=index)
    return result, evidence_from_retrieval(
        result, lexical=index, hypothesis_for_doc={"Transfer": "interp_t", "Appeal": "interp_a"},
        source_ref_prefix="domain-pack:cpasf@0.1.0", **kw)


def test_retrieval_evidence_is_similarity_unknown_inferred_never_supporting():
    _, items = _evidence()
    assert items
    for item in items:
        assert item.method is EvidenceMethod.SIMILARITY
        assert item.stance is EvidenceStance.UNKNOWN
        assert item.authority is EvidenceAuthority.INFERRED
        assert "not approval" in item.rationale and not hasattr(item, "confidence")


def test_candidates_without_a_hypothesis_are_skipped_not_invented():
    result, items = _evidence(query="TRANSFER_EVENT taxable value")
    assert "Exemption" in result.ranked_ids
    assert {i.hypothesis_id for i in items} <= {"interp_t", "interp_a"}


def test_evidence_binds_source_text_digest_classification_and_replay():
    _, a = _evidence(classification=DataClassification.CONFIDENTIAL)
    _, b = _evidence(classification=DataClassification.CONFIDENTIAL)
    assert a[0].source.classification is DataClassification.CONFIDENTIAL
    assert a[0].source.source_ref == "domain-pack:cpasf@0.1.0:Transfer"
    assert len(a[0].source.content_digest) == 64
    assert (a[0].replay.input_digest, a[0].replay.parameters_digest,
            a[0].replay.result_digest) == (b[0].replay.input_digest,
                                           b[0].replay.parameters_digest,
                                           b[0].replay.result_digest)


def test_replay_parameters_change_when_the_glossary_changes():
    _, plain = _evidence()
    _, glossed = _evidence(index=BM25Index(DOCS, glossary=Glossary({"xfer": ("transfer",)})))
    assert plain[0].replay.parameters_digest != glossed[0].replay.parameters_digest


def test_replay_parameters_capture_every_retrieval_setting():
    index = BM25Index(DOCS)

    def digest(**kw):
        r = retrieve("TRANSFER_EVENT", lexical=index, **kw)
        return evidence_from_retrieval(r, lexical=index, hypothesis_for_doc={"Transfer": "i"},
                                       source_ref_prefix="p")[0].replay.parameters_digest
    base = digest()
    assert base == digest()
    for change in ({"rrf_k": 30}, {"top_k": 2}, {"min_lexical_score": 0.1}):
        assert digest(**change) != base, change
    dense = {"dense_ranker": lambda q: [("Transfer", 0.9)]}
    assert digest(dense_descriptor="fake/embed-1", **dense) != digest(dense_descriptor="fake/embed-2", **dense)


def test_retrieval_evidence_fits_an_investigation_packet_without_a_score():
    index = BM25Index(DOCS)
    packet = InvestigationPacket(artifact_ref="LEGACY.XFER_DT")
    packet.add_interpretation(CompetingInterpretation(meaning="transfer event",
                                                      canonical_concept="Transfer", id="interp_t"))
    result = retrieve("TRANSFER_EVENT", lexical=index)
    for item in evidence_from_retrieval(result, lexical=index,
                                        hypothesis_for_doc={"Transfer": "interp_t"},
                                        source_ref_prefix="pack"):
        packet.add_evidence(item)
    assert packet.stance_matrix("interp_t") == {
        "similarity": {"supports": 0, "contradicts": 0, "unknown": 1}}


# ---- architecture ----------------------------------------------------------

@pytest.mark.parametrize("filename", ["lexical.py", "hybrid.py"])
def test_retrieval_modules_cannot_reach_the_network_or_bypass_the_egress_gate(filename):
    banned = {"embeddings", "urllib", "http", "requests", "socket", "httpx"}
    tree = ast.parse((SOURCE / filename).read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in banned:
                found.append(node.module)
        elif isinstance(node, ast.Import):
            found += [a.name for a in node.names if a.name.split(".")[0] in banned]
    assert found == []
