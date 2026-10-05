"""Domain Packs — versioned installable domain knowledge (spec §17).

The engine stays generic; the pack carries code sets, invariants, known
legacy patterns, reference data, and reconciliation requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CodeSet:
    name: str
    mappings: dict[str, str]           # legacy code → canonical code
    discarded: set[str] = field(default_factory=set)


@dataclass
class DomainPack:
    name: str
    version: str
    canonical_concepts: dict[str, str] = field(default_factory=dict)  # id → definition
    code_sets: dict[str, CodeSet] = field(default_factory=dict)
    invariants: list[tuple[str, object]] = field(default_factory=list)  # (desc, callable)
    known_patterns: list[str] = field(default_factory=list)
    valid_from: str = ""
    golden_records: list[dict] = field(default_factory=list)

    def translate(self, code_set: str, legacy_value: str) -> str:
        cs = self.code_sets[code_set]
        if legacy_value in cs.mappings:
            return cs.mappings[legacy_value]
        raise KeyError(f"unmapped code {legacy_value!r} in {code_set}")

    def loss_report(self, code_set: str) -> dict[str, object]:
        """Semantic loss = legacy codes the pack cannot represent (§25)."""
        cs = self.code_sets[code_set]
        return {"code_set": code_set,
                "discarded": sorted(cs.discarded),
                "representable": len(cs.mappings)}
