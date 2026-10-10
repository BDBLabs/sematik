"""Core semantic model: assertions, provenance, temporal context, derivation."""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


class DerivationStatus(enum.Enum):
    OBSERVED_FACT = "observed_fact"
    REPORTED_FACT = "reported_fact"
    DERIVED_VALUE = "derived_value"
    ESTIMATE = "estimate"
    INFERENCE = "inference"
    AUTHORIZED_DETERMINATION = "authorized_determination"
    REFERENCE_VALUE = "reference_value"
    SYSTEM_ARTIFACT = "system_artifact"


@dataclass(frozen=True)
class Provenance:
    source_system: str
    source_database: str = ""
    source_table: str = ""
    source_field: str = ""
    source_record: str = ""
    snapshot_id: str = ""

    def ref(self) -> str:
        parts = [p for p in (self.source_system, self.source_database,
                             self.source_table, self.source_field,
                             self.source_record) if p]
        return "/".join(parts)


@dataclass(frozen=True)
class TemporalContext:
    """Distinct temporal dimensions must not be flattened (spec §9)."""

    effective_date: date | None = None
    transaction_date: datetime | None = None
    system_recorded_date: datetime | None = None
    observation_date: date | None = None
    filing_date: datetime | None = None
    period: str = ""

    def known_dimensions(self) -> list[str]:
        return [k for k, v in self.__dict__.items() if v not in (None, "")]


@dataclass(frozen=True)
class Confidence:
    """Decomposable confidence — never a bare number (spec §14).

    ``calibrated`` marks whether ``overall`` is backed by an independent
    calibration set (e.g. labeled mappings) or is a heuristic midpoint.
    Discovery hypotheses produced by heuristics are uncalibrated by default
    (see :meth:`from_evidence_strength`); human-asserted confidences in
    approved Mappings default to calibrated.  Entropy must refuse to
    normalize uncalibrated values (#36)."""

    overall: float
    drivers: tuple[str, ...] = ()
    calibrated: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.overall <= 1.0:
            raise ValueError("confidence must be in [0,1]")

    @classmethod
    def from_evidence_strength(cls, strength: str,
                                drivers: tuple[str, ...] = ()) -> "Confidence":
        """Create an *uncalibrated* Confidence from an ordinal evidence
        strength (weak/moderate/strong) until a calibration set exists
        (#36).

        The numeric midpoint is a placeholder, not a probability — the
        ``calibrated`` flag ensures entropy and other numeric consumers
        refuse or flag it.
        """
        if strength == "weak":
            value = 0.33
        elif strength == "moderate":
            value = 0.5
        elif strength == "strong":
            value = 0.75
        else:
            raise ValueError(
                f"evidence strength must be 'weak', 'moderate', or 'strong'; got {strength!r}")
        return cls(value, drivers, calibrated=False)


@dataclass(frozen=True)
class Assertion:
    """A semantic assertion richer than a key/value pair (spec §4)."""

    concept: str
    value: Any
    units: str = ""
    code_set: str = ""
    datatype: str = ""
    original_value: Any = None
    derivation: DerivationStatus = DerivationStatus.OBSERVED_FACT
    provenance: Provenance = field(default_factory=lambda: Provenance(""))
    temporal: TemporalContext = field(default_factory=TemporalContext)
    authority: str = ""
    confidence: Confidence = field(default_factory=lambda: Confidence(1.0))
    transformation_history: tuple[str, ...] = ()
    conflict_status: str = "none"
    validation_state: str = "unvalidated"
    review_state: str = "unreviewed"
    id: str = field(default_factory=lambda: "asrt_" + uuid.uuid4().hex[:12])

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"concept": self.concept, "value": self.value, "units": self.units,
             "datatype": self.datatype, "provenance": self.provenance.ref(),
             "derivation": self.derivation.value}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class SemanticHypothesis:
    candidate_meaning: str
    concept: str
    confidence: Confidence
    evidence_basis: str = ""  # what produced this hypothesis: heuristic/rule/evidence (#36)
    supporting: list[str] = field(default_factory=list)
    contradicting: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    affected_records: int = 0
    proposed_mapping: str = ""
    id: str = field(default_factory=lambda: "hyp_" + uuid.uuid4().hex[:12])


@dataclass
class SemanticQuestion:
    """First-class ambiguity blocking conversion (spec §15)."""

    concept: str
    candidate_interpretations: list[str]
    affected_records: int
    downstream_consequences: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    resolution: str | None = None
    resolved_by: str = ""
    rank: float = 0.0
    id: str = field(default_factory=lambda: "q_" + uuid.uuid4().hex[:12])

    def blocking(self) -> bool:
        return self.resolution is None
