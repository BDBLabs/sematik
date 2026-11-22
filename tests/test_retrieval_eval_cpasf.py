"""ADR-0006 section 10: measured retrieval baselines over a labeled CPASF set.

READ THIS BEFORE TRUSTING ANY NUMBER HERE. The labels and the glossary are
PROVISIONAL: written by one AI author, from general domain knowledge, with no
subject-matter-expert review, and the glossary was written with the same list
of abbreviations in mind as the queries. Recall@5 of 1.0 with the glossary is
therefore close to circular and says nothing about real agency schemas. These
numbers are pinned as REGRESSION GUARDS (a change means the retriever, glossary
or eval set changed) and to demonstrate the harness. A held-out, SME-authored
set from real legacy schemas is required before any quality claim."""

import json
import pathlib

import pytest

from sematik.cpasf_pack import cpasf_pack
from sematik.hybrid import RetrievalResult, retrieve
from sematik.lexical import BM25Index, Glossary
from sematik.retrieval_eval import LabeledQuery, evaluate_retriever

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "retrieval_eval_cpasf.json"


@pytest.fixture(scope="module")
def reports():
    data = json.loads(FIXTURE.read_text())
    cases = [LabeledQuery(c["id"], c["query"], frozenset(c["relevant"]), tuple(c["tags"]),
                          c.get("notes", "")) for c in data["cases"]]
    pack = cpasf_pack()
    plain = BM25Index(pack.canonical_concepts)
    glossed = BM25Index(pack.canonical_concepts, glossary=Glossary(pack.glossary))
    return {
        "meta": data["meta"], "n": len(cases),
        "lexical": evaluate_retriever(cases, lambda q: retrieve(q, lexical=plain)),
        "glossary": evaluate_retriever(cases, lambda q: retrieve(q, lexical=glossed)),
    }


def test_fixture_is_labelled_provisional_so_it_cannot_pass_as_validated(reports):
    meta = reports["meta"]
    assert meta["status"] == "PROVISIONAL" and "NOT been reviewed" in meta["review_required"]
    assert reports["n"] == 30


def test_pinned_lexical_only_baseline(reports):
    r = reports["lexical"]
    assert (r.answerable, r.unanswerable) == (25, 5)
    assert {k: round(v, 3) for k, v in r.recall_at.items()} == {1: 0.52, 5: 0.64, 10: 0.64}
    assert round(r.mrr, 3) == 0.58
    assert r.abstained_on_answerable == ("c01", "c03", "c08", "c10", "c12", "c14", "c18", "c20")
    assert round(r.recall_by_tag["abbreviation"][5], 3) == 0.526


def test_pinned_glossary_expanded_baseline(reports):
    r = reports["glossary"]
    assert {k: round(v, 3) for k, v in r.recall_at.items()} == {1: 0.76, 5: 1.0, 10: 1.0}
    assert round(r.mrr, 3) == 0.873
    assert r.abstained_on_answerable == () and r.misses_at[5] == ()


def test_glossary_expansion_must_never_reduce_recall_or_mrr(reports):
    plain, glossed = reports["lexical"], reports["glossary"]
    assert all(glossed.recall_at[k] >= plain.recall_at[k] for k in plain.recall_at)
    assert glossed.mrr >= plain.mrr


def test_known_limitation_lexical_coincidence_is_reported_not_hidden(reports):
    # LAST_CHANGE_DATE is unanswerable but shares the word 'change' with the
    # Transfer definition. Lexical abstention cannot be trusted on its own.
    for name in ("lexical", "glossary"):
        r = reports[name]
        assert r.answered_on_unanswerable == ("u05",)
        assert r.correct_abstentions == 4


# ---- harness mechanics, independent of the corpus --------------------------

def _stub(table):
    def retrieve_fn(query):
        ids = table.get(query)
        return RetrievalResult(query, (), ids is None, "", ("stub",), ()) if ids is None \
            else _Ranked(ids)
    return retrieve_fn


class _Ranked:
    abstained = False

    def __init__(self, ids):
        self.ranked_ids = tuple(ids)


def test_evaluator_computes_recall_mrr_abstention_and_tags():
    cases = [
        LabeledQuery("a", "qa", frozenset({"X"}), ("t1",)),
        LabeledQuery("b", "qb", frozenset({"Y"}), ("t1", "t2")),
        LabeledQuery("c", "qc", frozenset({"Z"}), ("t2",)),
        LabeledQuery("d", "qd", frozenset(), ("unanswerable",)),
        LabeledQuery("e", "qe", frozenset(), ("unanswerable",)),
    ]
    r = evaluate_retriever(cases, _stub({"qa": ["X", "Q"], "qb": ["Q", "Y"], "qd": ["W"]}),
                           ks=(1, 2))
    assert r.recall_at == {1: pytest.approx(1 / 3), 2: pytest.approx(2 / 3)}
    assert r.mrr == pytest.approx((1 + 0.5 + 0) / 3)
    assert r.abstained_on_answerable == ("c",)
    assert r.answered_on_unanswerable == ("d",) and r.correct_abstentions == 1
    assert r.misses_at[1] == ("b", "c")
    assert r.recall_by_tag["t1"] == {1: 0.5, 2: 1.0}
    assert r.recall_by_tag["t2"] == {1: 0.0, 2: 0.5}


def test_evaluator_input_validation():
    ok = LabeledQuery("a", "q", frozenset({"X"}))
    with pytest.raises(ValueError):
        evaluate_retriever([], _stub({}))
    with pytest.raises(ValueError):
        evaluate_retriever([ok], _stub({}), ks=(0,))
    with pytest.raises(ValueError, match="answerable"):
        evaluate_retriever([LabeledQuery("u", "q", frozenset())], _stub({}))
    with pytest.raises(ValueError):
        LabeledQuery(" ", "q", frozenset({"X"}))
