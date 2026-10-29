"""Hybrid retrieval: lexical + optional dense, fused by rank, with abstention.

Retrieval proposes where to investigate. Nothing here approves a mapping or
produces a Confidence value: fused scores are ordinal evidence of resemblance
and every emitted ``EvidenceItem`` has stance UNKNOWN and authority INFERRED
(ADR-0003, ADR-0006 sections 2, 5 and 10). The dense side is an injected ranker
so that any embedding call stays behind the egress gate (ADR-0006 section 8).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from .egress import DataClassification
from .investigation import (EvidenceAuthority, EvidenceItem, EvidenceMethod,
                            EvidenceStance, ReplayRecord, SourceSpan)
from .lexical import BM25Index, LexicalHit

RETRIEVAL_VERSION = "hybrid-rrf-1"
DenseHit = tuple[str, float]
DenseRanker = Callable[[str], Sequence[DenseHit]]


@dataclass(frozen=True)
class FusedHit:
    doc_id: str
    score: float                         # reciprocal-rank-fusion score; ordinal only
    ranks: Mapping[str, int]             # method -> 1-based rank
    lexical: LexicalHit | None = None
    dense_score: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ranks", MappingProxyType(dict(self.ranks)))


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    hits: tuple[FusedHit, ...]
    abstained: bool
    reason: str
    methods: tuple[str, ...]             # methods that were configured
    methods_with_hits: tuple[str, ...]   # methods that actually contributed
    parameters: Mapping[str, object] = field(default_factory=dict)   # for replay

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @property
    def ranked_ids(self) -> tuple[str, ...]:
        return tuple(h.doc_id for h in self.hits)


def reciprocal_rank_fusion(rankings: Mapping[str, Sequence[str]], *,
                           k: int = 60) -> dict[str, float]:
    """score(d) = sum over methods of 1 / (k + rank_m(d)), rank 1-based."""
    if k <= 0:
        raise ValueError("rrf k must be positive")
    scores: dict[str, float] = {}
    for ranking in rankings.values():
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def _clean_dense(raw: Sequence[DenseHit], floor: float | None) -> list[DenseHit]:
    seen: set[str] = set()
    cleaned: list[DenseHit] = []
    for item in raw:
        doc_id, score = item
        if not isinstance(doc_id, str) or not isinstance(score, (int, float)) \
                or isinstance(score, bool) or not math.isfinite(score):
            raise ValueError("dense ranker must return (str id, finite float score) pairs")
        if doc_id in seen or (floor is not None and score < floor):
            continue
        seen.add(doc_id)
        cleaned.append((doc_id, float(score)))
    cleaned.sort(key=lambda p: (-p[1], p[0]))
    return cleaned


def retrieve(query: str, *, lexical: BM25Index, dense_ranker: DenseRanker | None = None,
             dense_descriptor: str = "", top_k: int = 10, min_lexical_score: float = 0.0,
             min_dense_score: float | None = None, rrf_k: int = 60) -> RetrievalResult:
    """Retrieve candidates, or abstain when no method has anything above its floor.

    ``dense_descriptor`` (provider/model/version of the injected ranker) is
    required whenever a dense ranker is supplied: evidence that cannot say which
    ranker produced it cannot be replayed (ADR-0006 section 2)."""
    if not query.strip():
        raise ValueError("query is required")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if dense_ranker is not None and not dense_descriptor.strip():
        raise ValueError("dense_descriptor is required when a dense ranker is supplied")
    parameters = {"top_k": top_k, "rrf_k": rrf_k, "min_lexical_score": min_lexical_score,
                  "min_dense_score": min_dense_score,
                  "dense_descriptor": dense_descriptor if dense_ranker is not None else None}
    lex_hits = [h for h in lexical.search(query, k=lexical.size)
                if h.score >= min_lexical_score]
    lex_by_id = {h.doc_id: h for h in lex_hits}
    rankings: dict[str, list[str]] = {}
    methods = ["lexical"]
    if lex_hits:
        rankings["lexical"] = [h.doc_id for h in lex_hits]
    dense_scores: dict[str, float] = {}
    if dense_ranker is not None:
        methods.append("dense")
        dense = _clean_dense(dense_ranker(query), min_dense_score)
        if dense:
            rankings["dense"] = [d for d, _ in dense]
            dense_scores = dict(dense)
    if not rankings:
        return RetrievalResult(query, (), True,
                               "no retrieval method produced a candidate above its floor",
                               tuple(methods), (), parameters)
    fused = reciprocal_rank_fusion(rankings, k=rrf_k)
    ordered = sorted(fused, key=lambda d: (-fused[d], d))[:top_k]
    hits = tuple(FusedHit(
        doc_id=d, score=fused[d],
        ranks={m: r.index(d) + 1 for m, r in rankings.items() if d in r},
        lexical=lex_by_id.get(d), dense_score=dense_scores.get(d)) for d in ordered)
    return RetrievalResult(query, hits, False, "", tuple(methods), tuple(rankings),
                           parameters)


def evidence_from_retrieval(
        result: RetrievalResult, *, lexical: BM25Index,
        hypothesis_for_doc: Mapping[str, str], source_ref_prefix: str,
        classification: DataClassification = DataClassification.INTERNAL,
        producer: str = "sematik.hybrid") -> list[EvidenceItem]:
    """Turn retrieved candidates into typed evidence for an investigation packet.

    Retrieval can only say "this resembles that": every item is method
    SIMILARITY, stance UNKNOWN, authority INFERRED. Candidates with no
    corresponding hypothesis are skipped, never invented.
    """
    parameters = {**lexical.params(), **result.parameters, "retrieval_version": RETRIEVAL_VERSION,
                  "methods": list(result.methods_with_hits)}
    items: list[EvidenceItem] = []
    for hit in result.hits:
        hypothesis_id = hypothesis_for_doc.get(hit.doc_id)
        if hypothesis_id is None:
            continue
        matched = ", ".join(hit.lexical.matched_terms) if hit.lexical else "none"
        items.append(EvidenceItem(
            hypothesis_id=hypothesis_id,
            stance=EvidenceStance.UNKNOWN,
            method=EvidenceMethod.SIMILARITY,
            authority=EvidenceAuthority.INFERRED,
            source=SourceSpan.from_text(
                source_ref=f"{source_ref_prefix}:{hit.doc_id}", locator=hit.doc_id,
                text=lexical.documents[hit.doc_id], classification=classification),
            replay=ReplayRecord.build(
                producer=producer, operation="hybrid_retrieval", version=RETRIEVAL_VERSION,
                inputs={"query": result.query, "index_digest": lexical.digest()},
                parameters=parameters,
                result=[(h.doc_id, round(h.score, 12), dict(h.ranks)) for h in result.hits]),
            producer_ref=producer,
            rationale=(f"Retrieved at rank(s) {dict(hit.ranks)}; matched terms: {matched}. "
                       "Resemblance only; not evidence of meaning and not approval."),
            scope={"method": "bm25+rrf" if "dense" in result.methods_with_hits else "bm25"},
        ))
    return items
