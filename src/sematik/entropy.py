"""Semantic entropy — a defensible measure of migration uncertainty (§76).

Formulation: for each concept c in a source environment, let p_c be the
normalized distribution over candidate meanings (from hypotheses). Define

    H(c) = - Σ_i p_i log2 p_i          (per-concept entropy, bits)
    S    = mean over concepts weighted by affected-record share

A column with a single high-confidence interpretation contributes ~0; a
column whose interpretations are uniform contributes log2(k). Ambiguity that
is resolved reduces S. Not a universal metric — a structural signal only.

Fail-closed (#36): entropy refuses to consume *uncalibrated* confidence
values — numeric scores produced by heuristics that were never calibrated
against labeled data.  Callers must either supply calibrated hypotheses or
use ``semantic_entropy_flagged`` for a best-effort score with a warning.
"""

from __future__ import annotations

import math
from collections import defaultdict

from .model import SemanticHypothesis


class UncalibratedConfidence(ValueError):
    """Raised when entropy is computed over uncalibrated confidences (#36)."""


def _check_calibrated(hypotheses: list[SemanticHypothesis]) -> None:
    """Every hypothesis must carry a calibrated confidence (#36)."""
    uncalibrated = [h for h in hypotheses if not h.confidence.calibrated]
    if uncalibrated:
        concepts = ", ".join(h.concept for h in uncalibrated)
        raise UncalibratedConfidence(
            f"cannot compute entropy over uncalibrated confidences; "
            f"uncalibrated concepts: {concepts} (#36). "
            f"Supply calibrated hypotheses or use semantic_entropy_flagged.")


def concept_entropy(hypotheses: list[SemanticHypothesis]) -> float:
    if not hypotheses:
        return 0.0
    _check_calibrated(hypotheses)
    confs = [max(h.confidence.overall, 1e-9) for h in hypotheses]
    total = sum(confs)
    ps = [c / total for c in confs]
    return -sum(p * math.log2(p) for p in ps)


def semantic_entropy(hypotheses: list[SemanticHypothesis]) -> float:
    """Weighted mean of per-concept entropy.

    Raises ``UncalibratedConfidence`` if any hypothesis is uncalibrated (#36).
    """
    if not hypotheses:
        return 0.0
    _check_calibrated(hypotheses)
    by_concept = defaultdict(list)
    for h in hypotheses:
        by_concept[h.concept].append(h)
    total_records = sum(h.affected_records for hs in by_concept.values() for h in hs) or 1
    weighted = 0.0
    for hs in by_concept.values():
        weight = sum(h.affected_records for h in hs) / total_records
        weighted += weight * concept_entropy(hs)
    return weighted


def semantic_entropy_flagged(hypotheses: list[SemanticHypothesis]) -> tuple[float, list[str]]:
    """Best-effort entropy with a warning list for uncalibrated hypotheses (#36).

    Unlike ``semantic_entropy``, this never raises — it returns the
    numeric score alongside a list of human-readable warnings for any
    uncalibrated inputs.  Use when the caller wants a score but must also
    surface the "semantic theater" limitation (spec §76).
    """
    warnings: list[str] = []
    uncalibrated = [h for h in hypotheses if not h.confidence.calibrated]
    if uncalibrated:
        for h in uncalibrated:
            basis = h.evidence_basis or "uncalibrated"
            warnings.append(
                f"uncalibrated confidence {h.confidence.overall} for concept "
                f"{h.concept} (basis: {basis}); entropy value is not a calibrated "
                f"probability")
    if not hypotheses:
        return 0.0, warnings
    # Compute entropy over the raw numeric values regardless of calibration,
    # but flag the limitation via warnings.
    by_concept = defaultdict(list)
    for h in hypotheses:
        by_concept[h.concept].append(h)
    total_records = sum(h.affected_records for hs in by_concept.values() for h in hs) or 1
    weighted = 0.0
    for hs in by_concept.values():
        confs = [max(h.confidence.overall, 1e-9) for h in hs]
        total = sum(confs)
        ps = [c / total for c in confs]
        concept_h = -sum(p * math.log2(p) for p in ps)
        weight = sum(h.affected_records for h in hs) / total_records
        weighted += weight * concept_h
    return weighted, warnings
