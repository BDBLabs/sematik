"""Typed evidence and semantic-investigation primitives.

This module belongs to the Discovery / Semantic Control boundary. It models
what was observed, how it bears on a hypothesis, and how another reviewer can
inspect or replay the observation.

It deliberately does not compute one blended confidence score. Evidence from
execution, documents, structure, similarity, and observed human process stays
typed so reviewers can reason about each dimension separately.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class EvidenceStance(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNKNOWN = "unknown"


class EvidenceMethod(str, Enum):
    EXECUTED = "executed"
    DOCUMENTARY = "documentary"
    STRUCTURAL = "structural"
    SIMILARITY = "similarity"
    PROCESS_OBSERVATION = "process_observation"
    HUMAN_ATTESTATION = "human_attestation"


class EvidenceAuthority(str, Enum):
    AUTHORITATIVE = "authoritative"
    OPERATIONAL = "operational"
    DESCRIPTIVE = "descriptive"
    INFERRED = "inferred"


class Replayability(str, Enum):
    REPLAYABLE = "replayable"
    INSPECTABLE = "inspectable"
    EPHEMERAL = "ephemeral"


class ProbeDisposition(str, Enum):
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"
    FAILED = "failed"


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, default=str, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class SourceSpan:
    """The inspectable source behind one evidence item.

    excerpt is optional because restricted environments may retain only a
    locator and digest in Sematik while the actual content remains in the
    source system.
    """

    source_ref: str
    locator: str
    content_digest: str
    excerpt: str = ""
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("source_ref is required")
        if not self.locator.strip():
            raise ValueError("locator is required")
        if len(self.content_digest) != 64:
            raise ValueError("content_digest must be a full SHA-256 hex digest")
        try:
            int(self.content_digest, 16)
        except ValueError as exc:
            raise ValueError("content_digest must be hexadecimal") from exc

    @classmethod
    def from_text(
        cls,
        *,
        source_ref: str,
        locator: str,
        text: str,
        retain_excerpt: bool = True,
        observed_at: datetime | None = None,
    ) -> "SourceSpan":
        return cls(
            source_ref=source_ref,
            locator=locator,
            content_digest=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            excerpt=text if retain_excerpt else "",
            observed_at=observed_at,
        )


@dataclass(frozen=True)
class ReplayRecord:
    """How an evidence-producing operation can be inspected or reproduced."""

    producer: str
    operation: str
    version: str
    input_digest: str
    parameters_digest: str
    result_digest: str
    replayability: Replayability
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def build(
        cls,
        *,
        producer: str,
        operation: str,
        version: str,
        inputs: Any,
        parameters: Mapping[str, Any],
        result: Any,
        replayability: Replayability = Replayability.REPLAYABLE,
    ) -> "ReplayRecord":
        return cls(
            producer=producer,
            operation=operation,
            version=version,
            input_digest=_digest(inputs),
            parameters_digest=_digest(dict(parameters)),
            result_digest=_digest(result),
            replayability=replayability,
        )


@dataclass(frozen=True)
class EvidenceItem:
    """A typed claim about how one observation bears on one hypothesis."""

    hypothesis_id: str
    stance: EvidenceStance
    method: EvidenceMethod
    authority: EvidenceAuthority
    source: SourceSpan
    replay: ReplayRecord
    producer_ref: str
    rationale: str = ""
    scope: Mapping[str, str] = field(default_factory=dict)
    id: str = field(default_factory=lambda: "ev_" + uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if not self.hypothesis_id.strip():
            raise ValueError("hypothesis_id is required")
        if not self.producer_ref.strip():
            raise ValueError("producer_ref is required")


@dataclass(frozen=True)
class FalsificationPrediction:
    """An observable prediction that could disprove an interpretation."""

    hypothesis_id: str
    statement: str
    observable: str
    failure_implication: str
    id: str = field(default_factory=lambda: "pred_" + uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if not all(
            part.strip()
            for part in (
                self.hypothesis_id,
                self.statement,
                self.observable,
                self.failure_implication,
            )
        ):
            raise ValueError("prediction fields must be non-empty")


@dataclass(frozen=True)
class EvidenceProbe:
    """A planned test of one falsification prediction."""

    hypothesis_id: str
    prediction_id: str
    name: str
    method: EvidenceMethod
    symmetric_group: str
    adversarial: bool = False
    parameters: Mapping[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: "probe_" + uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if not all(
            part.strip()
            for part in (
                self.hypothesis_id,
                self.prediction_id,
                self.name,
                self.symmetric_group,
            )
        ):
            raise ValueError("probe identity fields must be non-empty")


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    disposition: ProbeDisposition
    evidence_ids: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.probe_id.strip():
            raise ValueError("probe_id is required")


@dataclass(frozen=True)
class CompetingInterpretation:
    """One possible meaning for the same source artifact."""

    meaning: str
    canonical_concept: str = ""
    id: str = field(default_factory=lambda: "interp_" + uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if not self.meaning.strip():
            raise ValueError("meaning is required")


@dataclass
class InvestigationPacket:
    """Review packet for one source artifact and its competing meanings."""

    artifact_ref: str
    interpretations: list[CompetingInterpretation] = field(default_factory=list)
    predictions: list[FalsificationPrediction] = field(default_factory=list)
    probes: list[EvidenceProbe] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)

    def _interpretation_ids(self) -> set[str]:
        return {item.id for item in self.interpretations}

    def add_interpretation(self, item: CompetingInterpretation) -> None:
        if item.id in self._interpretation_ids():
            raise ValueError(f"duplicate interpretation {item.id}")
        self.interpretations.append(item)

    def add_prediction(self, prediction: FalsificationPrediction) -> None:
        if prediction.hypothesis_id not in self._interpretation_ids():
            raise ValueError("prediction must reference a packet interpretation")
        self.predictions.append(prediction)

    def add_probe(self, probe: EvidenceProbe) -> None:
        if probe.hypothesis_id not in self._interpretation_ids():
            raise ValueError("probe must reference a packet interpretation")
        prediction_ids = {p.id for p in self.predictions}
        if probe.prediction_id not in prediction_ids:
            raise ValueError("probe must reference a packet prediction")
        self.probes.append(probe)

    def add_evidence(self, item: EvidenceItem) -> None:
        if item.hypothesis_id not in self._interpretation_ids():
            raise ValueError("evidence must reference a packet interpretation")
        self.evidence.append(item)

    def evidence_for(self, interpretation_id: str) -> list[EvidenceItem]:
        if interpretation_id not in self._interpretation_ids():
            raise KeyError(interpretation_id)
        return [
            item for item in self.evidence
            if item.hypothesis_id == interpretation_id
        ]

    def stance_matrix(self, interpretation_id: str) -> dict[str, dict[str, int]]:
        """Return typed counts without collapsing evidence into one score."""

        matrix: dict[str, dict[str, int]] = {}
        for item in self.evidence_for(interpretation_id):
            method = item.method.value
            stance = item.stance.value
            matrix.setdefault(
                method,
                {value.value: 0 for value in EvidenceStance},
            )
            matrix[method][stance] += 1
        return matrix

    def validate_symmetric_probe_coverage(self) -> list[str]:
        """Find probe families that do not test every interpretation."""

        interpretation_ids = self._interpretation_ids()
        by_group: dict[str, set[str]] = {}
        for probe in self.probes:
            by_group.setdefault(
                probe.symmetric_group, set()
            ).add(probe.hypothesis_id)
        return [
            group
            for group, covered in sorted(by_group.items())
            if covered != interpretation_ids
        ]


@dataclass(frozen=True)
class SemanticPrecedent:
    """A prior adjudicated mapping that may inform a new investigation.

    A precedent carries its original scope and evidence references. It does not
    transfer confidence or authority to a new source system.
    """

    source_artifact: str
    canonical_concept: str
    mapping_digest: str
    approval_ref: str
    evidence_refs: tuple[str, ...]
    system_scope: str
    version_scope: str = ""
    temporal_scope: str = ""
    known_differences: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        required = (
            self.source_artifact,
            self.canonical_concept,
            self.mapping_digest,
            self.approval_ref,
            self.system_scope,
        )
        if not all(value.strip() for value in required):
            raise ValueError(
                "semantic precedent must retain mapping, approval, and scope"
            )


@dataclass(frozen=True)
class ProcessObservation:
    """Authorized observation of work performed in a source application.

    This is the safe boundary for a future desktop/process-observation agent.
    It records a business-process event, not raw keystrokes or credentials.
    The observation is unknown-stance until an investigation explicitly
    relates it to a semantic hypothesis.
    """

    application: str
    action: str
    object_ref: str
    actor_ref: str
    session_ref: str
    source_locator: str
    content_digest: str
    occurred_at: datetime
    notes: str = ""

    def __post_init__(self) -> None:
        required = (
            self.application,
            self.action,
            self.object_ref,
            self.actor_ref,
            self.session_ref,
            self.source_locator,
        )
        if not all(value.strip() for value in required):
            raise ValueError(
                "process observation identity fields must be non-empty"
            )
        if len(self.content_digest) != 64:
            raise ValueError(
                "process observation requires a full SHA-256 digest"
            )

    def as_uninterpreted_evidence(
        self, *, hypothesis_id: str, producer_ref: str
    ) -> EvidenceItem:
        payload = {
            "application": self.application,
            "action": self.action,
            "object_ref": self.object_ref,
            "actor_ref": self.actor_ref,
            "session_ref": self.session_ref,
            "occurred_at": self.occurred_at.isoformat(),
        }
        source = SourceSpan(
            source_ref=f"process:{self.application}",
            locator=self.source_locator,
            content_digest=self.content_digest,
            excerpt=self.notes,
            observed_at=self.occurred_at,
        )
        replay = ReplayRecord.build(
            producer=producer_ref,
            operation="process_observation",
            version="1",
            inputs=payload,
            parameters={},
            result=payload,
            replayability=Replayability.INSPECTABLE,
        )
        return EvidenceItem(
            hypothesis_id=hypothesis_id,
            stance=EvidenceStance.UNKNOWN,
            method=EvidenceMethod.PROCESS_OBSERVATION,
            authority=EvidenceAuthority.OPERATIONAL,
            source=source,
            replay=replay,
            producer_ref=producer_ref,
            rationale=(
                "raw process observation; stance requires explicit interpretation"
            ),
        )
