"""Semantic entropy — a defensible measure of migration uncertainty (§76).

Formulation: for each concept c in a source environment, let p_c be the
normalized distribution over candidate meanings (from hypotheses). Define

    H(c) = - Σ_i p_i log2 p_i          (per-concept entropy, bits)
    S    = mean over concepts weighted by affected-record share

A column with a single high-confidence interpretation contributes ~0; a
column whose interpretations are uniform contributes log2(k). Ambiguity that
is resolved reduces S. Not a universal metric — a structural signal only.
"""

from __future__ import annotations

import math
from collections import defaultdict

from .model import SemanticHypothesis


def concept_entropy(hypotheses: list[SemanticHypothesis]) -> float:
    if not hypotheses:
        return 0.0
    confs = [max(h.confidence.overall, 1e-9) for h in hypotheses]
    total = sum(confs)
    ps = [c / total for c in confs]
    return -sum(p * math.log2(p) for p in ps)


def semantic_entropy(hypotheses: list[SemanticHypothesis]) -> float:
    by_concept = defaultdict(list)
    for h in hypotheses:
        by_concept[h.concept].append(h)
    total_records = sum(h.affected_records for hs in by_concept.values() for h in hs) or 1
    weighted = 0.0
    for hs in by_concept.values():
        weight = sum(h.affected_records for h in hs) / total_records
        weighted += weight * concept_entropy(hs)
    return weighted
