"""Lexical retrieval: identifier tokenization, glossary expansion, BM25 (ADR-0006 s10)."""

import pytest

from sematik.lexical import BM25Index, Glossary, tokenize

DOCS = {
    "Transfer": "A change of ownership or other transfer event",
    "Appeal": "A contest of an assessed conclusion",
    "Valuation": "A valued component (land, improvements, exemptions) of an assessment",
}


@pytest.mark.parametrize("text,expected", [
    ("AV_LND_01", ["av", "lnd"]),
    ("LandAssessedValue", ["land", "assessed", "value"]),
    ("PROP13_BASE_AMT", ["prop", "base", "amt"]),
    ("APNValue", ["apn", "value"]),
    ("Base-year value component", ["base", "year", "value", "component"]),
    ("A change of ownership", ["change", "ownership"]),          # stopwords dropped
    ("improvements", ["improvement"]),                            # plural stripped
    ("class", ["class"]),                                         # 'ss' kept
    ("PARCEL_NO", ["parcel", "no"]),                              # 'no' is not a stopword
    ("", []),
    ("___", []),
])
def test_tokenize_identifiers_and_prose(text, expected):
    assert tokenize(text) == expected


def test_numeric_suffixes_are_dropped_unless_requested():
    assert tokenize("AV_LND_01") == ["av", "lnd"]
    assert tokenize("AV_LND_01", keep_numeric=True) == ["av", "lnd", "01"]


def test_glossary_validates_and_is_order_independent():
    with pytest.raises(ValueError, match="single token"):
        Glossary({"av lnd": ("land",)})
    with pytest.raises(ValueError, match="no usable expansion"):
        Glossary({"av": ("the of",)})
    a = Glossary({"av": ("assessed value",), "lnd": ("land",)})
    b = Glossary({"lnd": ("land",), "av": ("assessed value",)})
    assert a.digest() == b.digest()
    assert a.digest() != Glossary({"av": ("assessed value",)}).digest()
    assert a.expansions_for("av") == ("assessed", "value")


def test_exact_identifier_tokens_rank_first_and_report_matched_terms():
    hits = BM25Index(DOCS).search("TRANSFER_EVENT")
    assert hits[0].doc_id == "Transfer"
    assert set(hits[0].matched_terms) == {"transfer", "event"}
    assert hits[0].expanded_terms == ()


def test_unrelated_query_returns_nothing_not_ranked_noise():
    assert BM25Index(DOCS).search("UI_THEME") == []


def test_glossary_expansion_widens_search_and_is_labelled():
    plain, glossed = BM25Index(DOCS), BM25Index(DOCS, glossary=Glossary({"xfer": ("transfer",)}))
    assert plain.search("XFER_DT") == []
    hit = glossed.search("XFER_DT")[0]
    assert hit.doc_id == "Transfer" and hit.expanded_terms == ("transfer",)
    analysis = glossed.analyze("XFER_DT")
    assert analysis.tokens == ("xfer", "dt") and analysis.expansions == ("transfer",)


def test_expansion_is_down_weighted_relative_to_literal_match():
    docs = {"Literal": "land value", "Expanded": "parcel acreage"}
    idx = BM25Index(docs, glossary=Glossary({"lnd": ("parcel",)}), expansion_weight=0.5)
    by_id = {h.doc_id: h for h in idx.search("LAND_LND")}
    assert by_id["Literal"].score > by_id["Expanded"].score


def test_ties_break_by_document_id_deterministically():
    docs = {"b_doc": "land value", "a_doc": "land value"}
    assert [h.doc_id for h in BM25Index(docs).search("land")] == ["a_doc", "b_doc"]


def test_rare_terms_outweigh_common_terms():
    docs = {"d1": "value alpha", "d2": "value beta", "d3": "value gamma", "d4": "value"}
    top = BM25Index(docs).search("value alpha")[0]
    assert top.doc_id == "d1"


def test_hits_expose_score_but_never_a_confidence():
    hit = BM25Index(DOCS).search("appeal")[0]
    assert hit.score > 0 and not hasattr(hit, "confidence")


def test_index_digest_changes_with_corpus_glossary_and_parameters():
    base = BM25Index(DOCS).digest()
    assert base == BM25Index(dict(reversed(list(DOCS.items())))).digest()
    assert base != BM25Index({**DOCS, "Appeal": "A different definition"}).digest()
    assert base != BM25Index(DOCS, glossary=Glossary({"av": ("value",)})).digest()
    assert base != BM25Index(DOCS, k1=1.2).digest()


@pytest.mark.parametrize("kwargs", [{"k1": 0}, {"b": 1.5}, {"expansion_weight": -0.1}])
def test_invalid_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        BM25Index(DOCS, **kwargs)


def test_empty_or_blank_corpus_is_rejected_and_k_must_be_positive():
    with pytest.raises(ValueError):
        BM25Index({})
    with pytest.raises(ValueError):
        BM25Index({"x": "  "})
    with pytest.raises(ValueError):
        BM25Index(DOCS).search("appeal", k=0)
