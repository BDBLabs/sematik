"""Mapping model — seven semantic levels (spec §13)."""

from __future__ import annotations

import json
import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from .model import Confidence


@dataclass(frozen=True)
class MappingLevel:
    level: int  # 1..7
    kind: str
    statement: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class Mapping:
    source_artifact: str            # e.g. "OLDDB.PARCEL.LNDVAL"
    canonical_concept: str          # e.g. "Assessment.ValueComponent[type=LAND].amount"
    target_artifact: str = ""
    levels: list[MappingLevel] = field(default_factory=list)
    confidence: Confidence = field(default_factory=lambda: Confidence(0.0))
    rule_refs: list[str] = field(default_factory=list)
    domain_pack: str = ""
    approved_by: str = ""
    approval_ref: str = ""           # question resolution / ticket
    version: str = ""
    id: str = field(default_factory=lambda: "map_" + uuid.uuid4().hex[:12])

    def add_level(self, level: int, kind: str, statement: str, **context) -> None:
        self.levels.append(MappingLevel(level=level, kind=kind,
                                        statement=statement, context=context))

    def digest(self) -> str:
        payload = json.dumps(
            {"source": self.source_artifact, "target": self.target_artifact,
             "concept": self.canonical_concept,
             "levels": [asdict(l) for l in self.levels],
             "rules": sorted(self.rule_refs), "pack": self.domain_pack},
            sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def complete(self) -> bool:
        seen = {l.level for l in self.levels}
        return seen == set(range(1, 8))

    def approved(self) -> bool:
        return bool(self.approved_by) and self.confidence.overall > 0
