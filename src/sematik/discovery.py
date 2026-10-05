"""Discovery plane: source profiling → hypotheses (spec §5).

Discovery *proposes*. It never approves mappings (ADR-0003). It must infer
meaning from behavior, not metadata — a field named VALUE is not evidence (§8).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable

from .model import Confidence, SemanticHypothesis


def profile_column(values: Iterable[Any]) -> dict[str, Any]:
    vals = list(values)
    non_null = [v for v in vals if v is not None]
    types = Counter(type(v).__name__ for v in non_null)
    uniques = Counter(str(v) for v in non_null)
    numeric = [v for v in non_null if isinstance(v, (int, float)) and not isinstance(v, bool)]
    profile = {
        "count": len(vals),
        "null_rate": 1 - len(non_null) / len(vals) if vals else 0.0,
        "types": dict(types),
        "distinct": len(uniques),
        "distinct_ratio": len(uniques) / len(non_null) if non_null else 0.0,
        "top_values": uniques.most_common(5),
        "min": min(numeric) if numeric else None,
        "max": max(numeric) if numeric else None,
        "mean": sum(numeric) / len(numeric) if numeric else None,
    }
    return profile


def shannon_entropy(values: Iterable[Any]) -> float:
    vals = [v for v in values if v is not None]
    if not vals:
        return 0.0
    counts = Counter(str(v) for v in vals)
    total = len(vals)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def candidate_relationships(tables: dict[str, list[dict[str, Any]]],
                            *, overlap_threshold: float = 0.9) -> list[dict[str, Any]]:
    """Heuristic FK-like discovery (spec §12): for every pair of columns in
    different tables, count the fraction of distinct values in the smaller
    side that appear in the larger side. It is a *candidate* relationship —
    confidence-tagged, evidence-backed, never authoritative — because databases
    routinely reuse values that do not imply FKs."""
    columns: list[tuple[str, str, set]] = []
    for table, rows in tables.items():
        keys = {k for r in rows for k in r.keys()}
        for k in keys:
            vals = {r.get(k) for r in rows if r.get(k) is not None}
            if vals:
                columns.append((table, k, vals))
    out = []
    for i, (t1, k1, v1) in enumerate(columns):
        for t2, k2, v2 in columns[i + 1:]:
            if t1 == t2:
                continue
            smaller, larger = (v1, v2) if len(v1) <= len(v2) else (v2, v1)
            overlap = len(smaller & larger) / max(len(smaller), 1)
            if overlap >= overlap_threshold and smaller:
                out.append({"from": [t1, k1] if len(v1) <= len(v2) else [t2, k2],
                            "to": [t2, k2] if len(v1) <= len(v2) else [t1, k1],
                            "overlap": round(overlap, 3),
                            "confidence": round(0.4 + 0.5 * overlap, 3),
                            "note": "candidate only — requires evidence from code/docs/SME"})
    return out


def hypotheses_for_column(name: str, profile: dict[str, Any]) -> list[SemanticHypothesis]:
    """Return candidate interpretations. Deliberately conservative: it names
    suspicion, not 'meaning'. A human decides (§15/§38)."""
    hyps: list[SemanticHypothesis] = []
    distinct_ratio = profile["distinct_ratio"]
    top = profile["top_values"]
    if distinct_ratio < 0.01 and len(top) <= 8:
        hyps.append(SemanticHypothesis(
            candidate_meaning=f"likely a code/flag column (low distinct ratio, {len(top)} dominant values)",
            concept="codeset_candidate", confidence=Confidence(0.6, ("cardinality", "dominance")),
            supporting=["low distinct_ratio", f"{len(top)} dominant values"], affected_records=profile["count"]))
    if distinct_ratio > 0.99 and profile["count"] > 1:
        hyps.append(SemanticHypothesis(
            candidate_meaning="likely an identifier column (near-unique)",
            concept="identifier_candidate", confidence=Confidence(0.65, ("uniqueness",)),
            supporting=["near-unique values"], affected_records=profile["count"]))
    types = set(profile["types"])
    if types == {"bool"} or types == {"int"} and profile["distinct"] == 2:
        hyps.append(SemanticHypothesis(
            candidate_meaning="likely a flag (boolean/binary)",
            concept="flag_candidate", confidence=Confidence(0.7, ("binary_domain",)),
            supporting=["two-value domain"], affected_records=profile["count"]))
    if profile["null_rate"] > 0.5:
        hyps.append(SemanticHypothesis(
            candidate_meaning="sparse field — possibly legacy/obsolete or conditional",
            concept="sparse_candidate", confidence=Confidence(0.55, ("null_rate",)),
            supporting=[f"null_rate={profile['null_rate']:.2f}"], affected_records=profile["count"]))
    if not hyps:
        hyps.append(SemanticHypothesis(
            candidate_meaning="meaning unresolved — needs documentation/SME review",
            concept="unknown", confidence=Confidence(0.2, ("insufficient_signal",)),
            contradicting=["no strong structural signal"], affected_records=profile["count"]))
    return hyps
