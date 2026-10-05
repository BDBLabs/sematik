"""Identity resolution — durable canonical identity independent of legacy
primary keys (spec §11). Deterministic strategies first; probabilistic
matching is an explicit, logged decision, not a default."""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid


def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in s if ch.isalnum())


def probabilistic_match(a: dict[str, str], b: dict[str, str],
                        keys: list[str], *, threshold: float = 0.8) -> tuple[bool, float, list[str]]:
    """Similarity over normalized key fields (spec §11: probabilistic matching
    must be explicit, logged, and confidence-tagged — never silent)."""
    if not keys:
        return False, 0.0, ["no keys supplied"]
    hits, misses = 0, 0
    misses_list = []
    for k in keys:
        if _norm(a.get(k, "")) == _norm(b.get(k, "")) and a.get(k):
            hits += 1
        else:
            misses += 1
            misses_list.append(k)
    confidence = hits / len(keys)
    return confidence >= threshold, round(confidence, 3), misses_list


@dataclass
class IdentityDecision:
    canonical_id: str
    source_system: str
    source_key: str
    strategy: str            # deterministic-exact | deterministic-normalized | probabilistic | manual
    confidence: float
    rationale: list[str] = field(default_factory=list)


@dataclass
class IdentityRegistry:
    by_canonical: dict[str, list[IdentityDecision]] = field(default_factory=dict)
    by_source: dict[tuple[str, str], str] = field(default_factory=dict)

    def resolve_exact(self, source_system: str, source_key: str) -> str | None:
        return self.by_source.get((source_system, source_key))

    def register(self, source_system: str, source_key: str, canonical_id: str | None = None,
                 *, strategy: str = "deterministic-exact", confidence: float = 1.0,
                 rationale: list[str] | None = None) -> str:
        if confidence < 0 or confidence > 1:
            raise ValueError("confidence in [0,1]")
        cid = canonical_id or "id_" + uuid.uuid4().hex[:10]
        d = IdentityDecision(canonical_id=cid, source_system=source_system,
                             source_key=source_key, strategy=strategy,
                             confidence=confidence, rationale=rationale or [])
        self.by_canonical.setdefault(cid, []).append(d)
        self.by_source[(source_system, source_key)] = cid
        return cid

    def lineage(self, canonical_id: str) -> list[IdentityDecision]:
        return list(self.by_canonical.get(canonical_id, []))
