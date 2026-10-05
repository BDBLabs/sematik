from sematik.model import SemanticQuestion
from sematik.questions import rank_questions, render_request


def test_rank_orders_by_impact():
    a = SemanticQuestion(concept="x", candidate_interpretations=["a", "b"],
                         affected_records=100, downstream_consequences=["d1", "d2"])
    b = SemanticQuestion(concept="y", candidate_interpretations=["a"],
                         affected_records=2_000_000, downstream_consequences=["d"])
    ranked = rank_questions([a, b])
    assert ranked[0] is b and ranked[0].rank > ranked[1].rank


def test_request_rendered_to_requests_dir(tmp_path):
    q = SemanticQuestion(concept="PROPSTAT", candidate_interpretations=["owner", "responsible party"],
                         affected_records=18422, downstream_consequences=["ownership target table"])
    path = render_request(q, tmp_path)
    assert path.exists()
    assert "PROPSTAT" in path.read_text()
