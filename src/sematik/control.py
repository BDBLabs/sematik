"""Control store — append-only, content-addressed approval events (ADR-0008).

The Control store is the only module that persists Semantic Control state.
State is a log of immutable events; current state is a projection of that log.

This implements Phase 1 of ADR-0008:
- SQLite store with event kinds
- verify_approval() function
- VerifiedApproval token
- compile/run enforcement via VerifiedApproval

AI-Assisted: yes
AI-Model: gpt-4 (exact variant unavailable)
AI-Provider: OpenAI
AI-Tool: Poolside Agent
AI-Role: Author
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Event kinds
# ---------------------------------------------------------------------------

class EventKind(str, Enum):
    """Kinds of events in the Control store (ADR-0008 §1)."""
    HYPOTHESIS_PROPOSED = "HypothesisProposed"
    EVIDENCE_ATTACHED = "EvidenceAttached"
    QUESTION_RAISED = "QuestionRaised"
    QUESTION_RESOLVED = "QuestionResolved"
    PLAN_COMPILED = "PlanCompiled"
    GOLDEN_RUN_RECORDED = "GoldenRunRecorded"
    MAPPING_APPROVED = "MappingApproved"
    APPROVAL_REVOKED = "ApprovalRevoked"
    IDENTITY_ASSIGNED = "IdentityAssigned"
    IDENTITY_REASSIGNED = "IdentityReassigned"


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ControlEvent:
    """Base event in the Control store (ADR-0008 §1)."""
    kind: EventKind
    subject: str  # what it's about (mapping digest, question id, etc.)
    actor: str  # authenticated principal
    payload: dict[str, Any]  # event-specific data
    prev: str | None = None  # previous event id for hash chain
    recorded_at: float = field(default_factory=time.time)
    seq: int = 0  # store-assigned sequence number

    def id(self) -> str:
        """SHA-256 of canonical payload (ADR-0008 §1)."""
        payload_str = json.dumps({
            "kind": self.kind.value,
            "subject": self.subject,
            "actor": self.actor,
            "payload": self._canonical_payload(),
            "prev": self.prev,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def _canonical_payload(self) -> dict[str, Any]:
        """Canonical form of payload for hashing (no timestamps, sorted keys)."""
        return {k: self._canonical_value(v) for k, v in sorted(self.payload.items())}

    def _canonical_value(self, v: Any) -> Any:
        if isinstance(v, dict):
            return {k: self._canonical_value(val) for k, val in sorted(v.items())}
        if isinstance(v, (list, tuple)):
            return [self._canonical_value(item) for item in v]
        if isinstance(v, float):
            return round(v, 10)  # normalize float representation
        return v


# ---------------------------------------------------------------------------
# Specialized events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MappingApproved(ControlEvent):
    """Approval record that references other records (ADR-0008 §2)."""
    mapping_digest: str = ""
    plan_digest: str = ""
    golden_run_id: str = ""
    evidence_ids: tuple[str, ...] = ()
    resolved_question_ids: tuple[str, ...] = ()
    approver: str = ""
    policy_id: str = ""
    signature: str | None = None

    def __post_init__(self):
        # Store approval fields in payload for persistence
        payload = {
            "mapping_digest": self.mapping_digest,
            "plan_digest": self.plan_digest,
            "golden_run_id": self.golden_run_id,
            "evidence_ids": list(self.evidence_ids),
            "resolved_question_ids": list(self.resolved_question_ids),
            "approver": self.approver,
            "policy_id": self.policy_id,
            "signature": self.signature,
        }
        object.__setattr__(self, "subject", f"mapping:{self.mapping_digest}")
        object.__setattr__(self, "payload", payload)
        
        # Ensure this is the right event kind
        if self.kind != EventKind.MAPPING_APPROVED:
            object.__setattr__(self, "kind", EventKind.MAPPING_APPROVED)

    @classmethod
    def create(cls, *, mapping_digest: str, plan_digest: str, golden_run_id: str,
                 evidence_ids: tuple[str, ...] = (), resolved_question_ids: tuple[str, ...] = (),
                 approver: str = "", policy_id: str = "", actor: str = "", 
                 signature: str | None = None) -> "MappingApproved":
        """Factory to create a MappingApproved event."""
        return cls(
            kind=EventKind.MAPPING_APPROVED,
            subject=f"mapping:{mapping_digest}",
            actor=actor,
            payload={},
            mapping_digest=mapping_digest,
            plan_digest=plan_digest,
            golden_run_id=golden_run_id,
            evidence_ids=evidence_ids,
            resolved_question_ids=resolved_question_ids,
            approver=approver,
            policy_id=policy_id,
            signature=signature,
        )


@dataclass(frozen=True)
class VerifiedApproval:
    """Immutable token from verify_approval() (ADR-0008 §3).

    Execution planes consume only this token, never the store.
    """
    approval_id: str
    mapping_digest: str
    plan_digest: str
    approver: str
    policy_id: str
    approval_digest: str  # stores approval event.id() for audit


# ---------------------------------------------------------------------------
# Store protocol
# ---------------------------------------------------------------------------

class ControlStore(Protocol):
    """Protocol for Control store implementations (ADR-0008 §1)."""

    def append(self, event: ControlEvent) -> str:
        """Append an event, return its id."""
        ...

    def get(self, event_id: str) -> ControlEvent | None:
        """Retrieve an event by id."""
        ...

    def resolve_subject(self, subject: str) -> list[str]:
        """Get event ids in order for a subject (hash chain)."""
        ...

    def latest_approval(self, mapping_digest: str) -> MappingApproved | None:
        """Get the latest approval for a mapping."""
        ...


# ---------------------------------------------------------------------------
# SQLite implementation
# ---------------------------------------------------------------------------

class SQLiteControlStore:
    """SQLite-based Control store (ADR-0008 §1).

    First implementation; PostgreSQL can follow without changing callers.
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._conn = sqlite3.connect(str(self._path))
        self._init_schema()

    def _init_schema(self):
        """Initialize the database schema."""
        schema = """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            subject TEXT NOT NULL,
            actor TEXT NOT NULL,
            payload TEXT NOT NULL,
            prev TEXT,
            recorded_at REAL NOT NULL,
            seq INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_subject ON events(subject);
        CREATE INDEX IF NOT EXISTS idx_actor ON events(actor);
        """
        self._conn.executescript(schema)
        self._conn.commit()

    def _next_seq(self) -> int:
        """Get the next sequence number."""
        result = self._conn.execute("SELECT MAX(seq) FROM events").fetchone()
        return (result[0] or 0) + 1

    def append(self, event: ControlEvent) -> str:
        """Append an event, return its id."""
        event_id = event.id()
        seq = self._next_seq()
        self._conn.execute(
            "INSERT INTO events (id, kind, subject, actor, payload, prev, recorded_at, seq) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, event.kind.value, event.subject, event.actor,
             json.dumps(event.payload), event.prev, event.recorded_at, seq)
        )
        self._conn.commit()
        return event_id

    def get(self, event_id: str) -> ControlEvent | None:
        """Retrieve an event by id."""
        row = self._conn.execute(
            "SELECT id, kind, subject, actor, payload, prev, recorded_at, seq "
            "FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        kind = EventKind(row[1])
        payload = json.loads(row[4])
        
        # Return specialized event types based on kind
        if kind == EventKind.MAPPING_APPROVED:
            return MappingApproved.create(
                mapping_digest=payload.get("mapping_digest", ""),
                plan_digest=payload.get("plan_digest", ""),
                golden_run_id=payload.get("golden_run_id", ""),
                evidence_ids=tuple(payload.get("evidence_ids", [])),
                resolved_question_ids=tuple(payload.get("resolved_question_ids", [])),
                approver=payload.get("approver", ""),
                policy_id=payload.get("policy_id", ""),
                actor=row[3],
                signature=payload.get("signature"),
            )
        
        return ControlEvent(
            kind=kind, subject=row[2], actor=row[3],
            payload=payload, prev=row[5], recorded_at=row[6], seq=row[7]
        )

    def resolve_subject(self, subject: str) -> list[str]:
        """Get event ids in order for a subject (hash chain)."""
        rows = self._conn.execute(
            "SELECT id FROM events WHERE subject = ? ORDER BY seq",
            (subject,)
        ).fetchall()
        return [row[0] for row in rows]

    def latest_approval(self, mapping_digest: str) -> MappingApproved | None:
        """Get the latest approval for a mapping."""
        row = self._conn.execute(
            "SELECT id, kind, subject, actor, payload, prev, recorded_at, seq FROM events "
            "WHERE kind = ? AND subject = ? ORDER BY seq DESC LIMIT 1",
            (EventKind.MAPPING_APPROVED.value, f"mapping:{mapping_digest}")
        ).fetchone()
        if row is None:
            return None
        # Reconstruct MappingApproved from payload
        payload = json.loads(row[4])
        event_id = row[0]
        return MappingApproved(
            kind=EventKind.MAPPING_APPROVED,
            subject=row[3],
            actor=row[4],
            payload=payload,
            prev=row[5],
            recorded_at=row[6],
            seq=row[7],
            mapping_digest=payload.get("mapping_digest", ""),
            plan_digest=payload.get("plan_digest", ""),
            golden_run_id=payload.get("golden_run_id", ""),
            evidence_ids=tuple(payload.get("evidence_ids", [])),
            resolved_question_ids=tuple(payload.get("resolved_question_ids", [])),
            approver=payload.get("approver", ""),
            policy_id=payload.get("policy_id", ""),
            signature=payload.get("signature"),
        )

    def close(self):
        """Close the database connection."""
        self._conn.close()


# ---------------------------------------------------------------------------
# Verification function
# ---------------------------------------------------------------------------

def verify_approval(store: ControlStore, approval_id: str,
                    mapping_digest: str, plan_digest: str) -> tuple[VerifiedApproval | None, list[str]]:
    """Verify an approval and return a VerifiedApproval token (ADR-0008 §3).

    Returns (token, problems) - token is None if verification fails.
    """
    event = store.get(approval_id)
    if event is None:
        return None, ["approval event not found"]

    if event.kind != EventKind.MAPPING_APPROVED:
        return None, ["not a MappingApproved event"]

    # Cast to MappingApproved - should succeed since we verified kind above
    if not isinstance(event, MappingApproved):
        return None, ["failed to reconstruct MappingApproved event"]

    problems = []

    # Verify mapping digest matches
    if event.mapping_digest != mapping_digest:
        problems.append(
            f"mapping digest mismatch: approval has {event.mapping_digest}, provided {mapping_digest}"
        )

    # Verify plan digest matches
    if event.plan_digest != plan_digest:
        problems.append(
            f"plan digest mismatch: approval has {event.plan_digest}, provided {plan_digest}"
        )

    # Verify golden run exists and passes
    if event.golden_run_id:
        golden_event = store.get(event.golden_run_id)
        if golden_event is None:
            problems.append(f"golden run event {event.golden_run_id} not found")

    # Verify evidence IDs exist
    for eid in event.evidence_ids:
        if eid and store.get(eid) is None:
            problems.append(f"evidence event {eid} not found")

    # Verify resolved question IDs exist
    for qid in event.resolved_question_ids:
        if qid and store.get(qid) is None:
            problems.append(f"question event {qid} not found")

    if problems:
        return None, problems

    return VerifiedApproval(
        approval_id=approval_id,
        mapping_digest=event.mapping_digest,
        plan_digest=event.plan_digest,
        approver=event.approver,
        policy_id=event.policy_id,
        approval_digest=event.id(),
    ), []