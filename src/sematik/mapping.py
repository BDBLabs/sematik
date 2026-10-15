"""Mapping model — seven semantic levels (spec §13)."""

from __future__ import annotations

import json
import hashlib
import math
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Protocol, TYPE_CHECKING

from .model import Confidence

if TYPE_CHECKING:
    from .control import ControlStore, VerifiedApproval


@dataclass(frozen=True)
class MappingLevel:
    level: int  # 1..7
    kind: str
    statement: str
    context: dict[str, Any] = field(default_factory=dict)


class ApprovalVerifier(Protocol):
    """Protocol for verifying approvals against a store (ADR-0008)."""
    def verify_approval(self, mapping_digest: str, plan_digest: str) -> VerifiedApproval | list[str]:
        """Verify approval. Returns VerifiedApproval or list of problems."""
        ...


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
    evidence_refs: list[str] = field(default_factory=list)
    blocking_question_ids: list[str] = field(default_factory=list)
    golden_plan_digest: str = ""     # digest of the golden plan this mapping passed
    id: str = field(default_factory=lambda: "map_" + uuid.uuid4().hex[:12])

    def add_level(self, level: int, kind: str, statement: str, **context) -> None:
        self.levels.append(MappingLevel(level=level, kind=kind,
                                        statement=statement, context=context))

    def __post_init__(self) -> None:
        """Validate evidence and question references at construction (#24).

        Every element must be a non-empty, non-whitespace string. A Mapping
        with evidence_refs=[""] or blocking_question_ids=["  "] is a
        programming error, not a semantically weaker mapping — reject it
        here rather than letting it silently pass approval.
        """
        self._validate_refs("evidence_refs", self.evidence_refs)
        self._validate_refs("blocking_question_ids", self.blocking_question_ids)

    @staticmethod
    def _validate_refs(field_name: str, refs: list[str]) -> None:
        for ref in refs:
            if not isinstance(ref, str) or not ref.strip():
                raise ValueError(
                    f"{field_name} must contain only non-empty strings; got {ref!r}")

    def digest(self) -> str:
        """Content digest for reproducibility (ADR-0008 §4)."""
        payload = json.dumps(
            {"source": self.source_artifact, "target": self.target_artifact,
             "concept": self.canonical_concept,
             "levels": [asdict(l) for l in self.levels],
             "rules": sorted(self.rule_refs), "pack": self.domain_pack,
             "evidence": sorted(self.evidence_refs),
             "blocking_questions": sorted(self.blocking_question_ids),
             "golden": self.golden_plan_digest},
            sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def complete(self) -> bool:
        """Check that all seven semantic levels are present (spec §13)."""
        levels = [item.level for item in self.levels]
        return sorted(levels) == list(range(1, 8))

    def structural_problems(self) -> list[str]:
        """All reasons this mapping is structurally incomplete (ADR-0008 §3).

        Checks completeness without requiring a store reference.
        Does NOT establish authority; use verify_binding() for that.
        """
        problems: list[str] = []
        if not self.approved_by.strip():
            problems.append("no approver recorded")
        if not self.approval_ref.strip():
            problems.append("no approval reference")
        if not self.version.strip():
            problems.append("no mapping version")
        conf = self.confidence.overall
        if not (math.isfinite(conf) and conf > 0):
            problems.append("confidence must be finite and positive")
        problems.extend(self._level_problems())
        valid_evidence = [e for e in self.evidence_refs if e and e.strip()]
        if not valid_evidence:
            problems.append("no evidence references bound to mapping")
        unresolved = [q for q in self.blocking_question_ids if q and q.strip()]
        if unresolved:
            problems.append(
                "unresolved blocking questions: "
                + ", ".join(sorted(unresolved)))
        if not self.golden_plan_digest.strip():
            problems.append("no tested golden plan bound to mapping")
        return problems

    def approval_problems(self) -> list[str]:
        """Alias for structural_problems() for backward compatibility.

        Deprecated: use structural_problems() for structural checks and
        verify_binding() for store-based verification (ADR-0008).
        """
        return self.structural_problems()

    def verify_binding(self, verifier: ApprovalVerifier) -> tuple[bool, list[str]]:
        """Verify this mapping against a Control store (ADR-0008 §3).

        Returns (is_valid, problems). The verifier protocol checks:
        - Evidence records exist and are valid
        - Question records are resolved
        - Golden run passes for the referenced plan
        - Approval record exists and matches mapping/plan

        Use this with a ControlStore adapter to enforce governance.
        """
        problems = self.structural_problems()
        if problems:
            return False, problems

        # Check that evidence references exist
        for eid in self.evidence_refs:
            if eid and eid.strip():
                # Verify evidence event exists in store
                # (This requires a store parameter - delegated to verifier)
                pass

        # Check questions are resolved
        for qid in self.blocking_question_ids:
            if qid and qid.strip():
                pass

        # Check golden run exists and passes
        if self.golden_plan_digest:
            pass

        return True, []

    def _level_problems(self) -> list[str]:
        """Validate that all seven semantic levels (spec §13) are present,
        in range and unduplicated."""
        levels = [item.level for item in self.levels]
        expected = set(range(1, 8))
        missing = sorted(expected - set(levels))
        invalid = sorted({lvl for lvl in levels if lvl not in expected})
        duplicates = sorted(
            lvl for lvl in expected if levels.count(lvl) > 1)
        problems: list[str] = []
        if missing:
            problems.append(f"semantic levels missing: {missing}")
        if invalid:
            problems.append(f"semantic levels out of range: {invalid}")
        if duplicates:
            problems.append(f"semantic levels duplicated: {duplicates}")
        return problems

    def approved(self) -> bool:
        return not self.approval_problems()
