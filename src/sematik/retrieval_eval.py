"""Evaluation helpers for semantic-retrieval experiments.

These metrics measure retrieval, not correctness of semantic adjudication.
A high recall@k says the known relevant concept/source was surfaced in the
candidate set. It does not mean Sematik proved the mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    relevant_ids: frozenset[str]
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if not self.query.strip():
            raise ValueError("query is required")
        if not self.relevant_ids:
            raise ValueError("at least one relevant id is required")


@dataclass(frozen=True)
class RetrievalEvaluation:
    total_cases: int
    recall_at: dict[int, float]
    misses_at: dict[int, tuple[str, ...]]


def evaluate_retrieval(
    cases: Sequence[RetrievalCase],
    ranker: Callable[[str], Sequence[str]],
    *,
    ks: tuple[int, ...] = (1, 5, 10),
) -> RetrievalEvaluation:
    """Evaluate whether at least one known-relevant item appears in top-k."""

    if not cases:
        raise ValueError("evaluation requires at least one case")
    if not ks or any(k <= 0 for k in ks):
        raise ValueError("ks must contain positive integers")

    hits = {k: 0 for k in ks}
    misses: dict[int, list[str]] = {k: [] for k in ks}

    for case in cases:
        ranked = list(ranker(case.query))
        for k in ks:
            top = set(ranked[:k])
            if top & case.relevant_ids:
                hits[k] += 1
            else:
                misses[k].append(case.case_id)

    total = len(cases)
    return RetrievalEvaluation(
        total_cases=total,
        recall_at={k: hits[k] / total for k in ks},
        misses_at={k: tuple(misses[k]) for k in ks},
    )


@dataclass(frozen=True)
class LabeledQuery:
    """A query with its known-relevant concept ids.

    An EMPTY ``relevant_ids`` means no concept applies: the correct behavior is
    to abstain. Labels are domain judgments; record who authored them in notes."""

    case_id: str
    query: str
    relevant_ids: frozenset[str]
    tags: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.query.strip():
            raise ValueError("case_id and query are required")


class RetrievalLike(Protocol):
    abstained: bool

    @property
    def ranked_ids(self) -> Sequence[str]: ...


@dataclass(frozen=True)
class RetrieverReport:
    answerable: int
    unanswerable: int
    recall_at: dict[int, float]
    mrr: float
    misses_at: dict[int, tuple[str, ...]]
    abstained_on_answerable: tuple[str, ...]     # false abstentions
    answered_on_unanswerable: tuple[str, ...]    # false retrievals (e.g. lexical coincidences)
    correct_abstentions: int
    recall_by_tag: dict[str, dict[int, float]] = field(default_factory=dict)


def evaluate_retriever(cases: Sequence[LabeledQuery],
                       retrieve: Callable[[str], RetrievalLike], *,
                       ks: tuple[int, ...] = (1, 5, 10)) -> RetrieverReport:
    """Recall@k and MRR over answerable cases, plus abstention behavior.

    Measures retrieval only: surfacing the right concept is not proof of
    meaning (see module docstring)."""
    if not cases:
        raise ValueError("evaluation requires at least one case")
    if not ks or any(k <= 0 for k in ks):
        raise ValueError("ks must contain positive integers")
    hits = {k: 0 for k in ks}
    misses: dict[int, list[str]] = {k: [] for k in ks}
    tag_hits: dict[str, dict[int, int]] = {}
    tag_total: dict[str, int] = {}
    reciprocal_ranks: list[float] = []
    false_abstain: list[str] = []
    false_retrieve: list[str] = []
    correct_abstain = answerable = unanswerable = 0
    for case in cases:
        result = retrieve(case.query)
        ranked = [] if result.abstained else list(result.ranked_ids)
        if not case.relevant_ids:
            unanswerable += 1
            if result.abstained:
                correct_abstain += 1
            else:
                false_retrieve.append(case.case_id)
            continue
        answerable += 1
        if result.abstained:
            false_abstain.append(case.case_id)
        first = next((i for i, d in enumerate(ranked, 1) if d in case.relevant_ids), None)
        reciprocal_ranks.append(1.0 / first if first else 0.0)
        for tag in case.tags:
            tag_total[tag] = tag_total.get(tag, 0) + 1
            tag_hits.setdefault(tag, {k: 0 for k in ks})
        for k in ks:
            if first is not None and first <= k:
                hits[k] += 1
                for tag in case.tags:
                    tag_hits[tag][k] += 1
            else:
                misses[k].append(case.case_id)
    if answerable == 0:
        raise ValueError("evaluation requires at least one answerable case")
    return RetrieverReport(
        answerable=answerable, unanswerable=unanswerable,
        recall_at={k: hits[k] / answerable for k in ks},
        mrr=sum(reciprocal_ranks) / answerable,
        misses_at={k: tuple(misses[k]) for k in ks},
        abstained_on_answerable=tuple(false_abstain),
        answered_on_unanswerable=tuple(false_retrieve),
        correct_abstentions=correct_abstain,
        recall_by_tag={t: {k: tag_hits[t][k] / tag_total[t] for k in ks} for t in tag_hits},
    )
