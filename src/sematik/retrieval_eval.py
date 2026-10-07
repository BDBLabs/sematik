"""Evaluation helpers for semantic-retrieval experiments.

These metrics measure retrieval, not correctness of semantic adjudication.
A high recall@k says the known relevant concept/source was surfaced in the
candidate set. It does not mean Sematik proved the mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence


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
