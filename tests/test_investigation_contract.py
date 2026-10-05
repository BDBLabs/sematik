import ast
from pathlib import Path

import pytest

from sematik.egress import (
    DataClassification,
    EgressDestination,
    EgressPolicy,
    EgressRequest,
    endpoint_allows_credentials,
)
from sematik.investigation import (
    CompetingInterpretation,
    EvidenceAuthority,
    EvidenceItem,
    EvidenceMethod,
    EvidenceProbe,
    EvidenceStance,
    FalsificationPrediction,
    InvestigationPacket,
    ProcessObservation,
    ReplayRecord,
    Replayability,
    SemanticPrecedent,
    SourceSpan,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "sematik"


def _source(text="evidence") -> SourceSpan:
    return SourceSpan.from_text(
        source_ref="doc:1",
        locator="page:1",
        text=text,
    )


def _replay(result="ok") -> ReplayRecord:
    return ReplayRecord.build(
        producer="test",
        operation="probe",
        version="1",
        inputs={"x": 1},
        parameters={"mode": "test"},
        result=result,
    )


def test_investigation_keeps_evidence_methods_separate():
    packet = InvestigationPacket(artifact_ref="LEGACY.TABLE.BASE_VAL")
    h = CompetingInterpretation(
        meaning="Prop 13 base-year value",
        canonical_concept="BaseYearComponent.amount",
    )
    packet.add_interpretation(h)

    packet.add_evidence(
        EvidenceItem(
            hypothesis_id=h.id,
            stance=EvidenceStance.SUPPORTS,
            method=EvidenceMethod.EXECUTED,
            authority=EvidenceAuthority.OPERATIONAL,
            source=_source("historical totals reconcile"),
            replay=_replay("balanced"),
            producer_ref="probe:historical-reconciliation",
        )
    )
    packet.add_evidence(
        EvidenceItem(
            hypothesis_id=h.id,
            stance=EvidenceStance.CONTRADICTS,
            method=EvidenceMethod.DOCUMENTARY,
            authority=EvidenceAuthority.DESCRIPTIVE,
            source=_source("screen label says Current Value"),
            replay=_replay("contradiction"),
            producer_ref="reviewer:model",
        )
    )

    matrix = packet.stance_matrix(h.id)
    assert matrix["executed"]["supports"] == 1
    assert matrix["documentary"]["contradicts"] == 1
    assert "score" not in matrix


def test_symmetric_probe_coverage_exposes_confirmation_bias():
    packet = InvestigationPacket(artifact_ref="LEGACY.TABLE.BASE_VAL")
    h1 = CompetingInterpretation(meaning="base-year value")
    h2 = CompetingInterpretation(meaning="current enrolled value")
    packet.add_interpretation(h1)
    packet.add_interpretation(h2)

    p1 = FalsificationPrediction(
        hypothesis_id=h1.id,
        statement="qualifying reassessment establishes a new component",
        observable="historical event sequence",
        failure_implication="interpretation is weakened",
    )
    p2 = FalsificationPrediction(
        hypothesis_id=h2.id,
        statement="value follows current enrollment changes",
        observable="historical enrollment sequence",
        failure_implication="interpretation is weakened",
    )
    packet.add_prediction(p1)
    packet.add_prediction(p2)

    packet.add_probe(
        EvidenceProbe(
            hypothesis_id=h1.id,
            prediction_id=p1.id,
            name="historical behavior",
            method=EvidenceMethod.EXECUTED,
            symmetric_group="historical-behavior",
        )
    )
    assert packet.validate_symmetric_probe_coverage() == [
        "historical-behavior"
    ]

    packet.add_probe(
        EvidenceProbe(
            hypothesis_id=h2.id,
            prediction_id=p2.id,
            name="historical behavior alternative",
            method=EvidenceMethod.EXECUTED,
            symmetric_group="historical-behavior",
            adversarial=True,
        )
    )
    assert packet.validate_symmetric_probe_coverage() == []


def test_process_observation_starts_unknown_not_supporting():
    text = "operator opens transfer screen and selects partial transfer"
    observation = ProcessObservation(
        application="Legacy CAMA",
        action="select transfer type",
        object_ref="parcel:123",
        actor_ref="staff:authorized",
        session_ref="session:1",
        source_locator="screen:transfer",
        content_digest=__import__("hashlib").sha256(
            text.encode("utf-8")
        ).hexdigest(),
        occurred_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
        notes=text,
    )
    item = observation.as_uninterpreted_evidence(
        hypothesis_id="interp_1",
        producer_ref="observer-agent:v1",
    )
    assert item.stance is EvidenceStance.UNKNOWN
    assert item.method is EvidenceMethod.PROCESS_OBSERVATION
    assert item.authority is EvidenceAuthority.OPERATIONAL


def test_semantic_precedent_requires_original_scope_and_approval():
    with pytest.raises(ValueError):
        SemanticPrecedent(
            source_artifact="LAND_ASSD",
            canonical_concept="Assessment.ValueComponent[LAND]",
            mapping_digest="abc",
            approval_ref="",
            evidence_refs=("ev_1",),
            system_scope="County A",
        )

    precedent = SemanticPrecedent(
        source_artifact="LAND_ASSD",
        canonical_concept="Assessment.ValueComponent[LAND]",
        mapping_digest="abc",
        approval_ref="approval:42",
        evidence_refs=("ev_1",),
        system_scope="County A / Legacy CAMA",
        version_scope="v7",
        temporal_scope="2018-2025",
        known_differences=("County B factors values differently",),
    )
    assert precedent.approval_ref == "approval:42"
    assert not hasattr(precedent, "confidence")


def test_conservative_egress_policy_denies_nonpublic_hosted_data():
    policy = EgressPolicy.conservative_government_default()

    public = EgressRequest.from_text(
        text="public schema description",
        classification=DataClassification.PUBLIC,
        destination=EgressDestination.HOSTED_EXTERNAL,
        purpose="semantic retrieval",
    )
    internal = EgressRequest.from_text(
        text="internal sample value",
        classification=DataClassification.INTERNAL,
        destination=EgressDestination.HOSTED_EXTERNAL,
        purpose="semantic retrieval",
    )

    assert policy.authorize(public).allowed
    assert not policy.authorize(internal).allowed


@pytest.mark.parametrize(
    "endpoint, expected",
    [
        ("https://api.example.com/v1/embeddings", True),
        ("http://localhost:8000/v1/embeddings", True),
        ("http://127.0.0.1:8000/v1/embeddings", True),
        ("http://[::1]:8000/v1/embeddings", True),
        ("http://embedding.internal:8000/v1/embeddings", False),
        ("http://198.51.100.10/v1/embeddings", False),
    ],
)
def test_credential_transport_policy(endpoint, expected):
    assert endpoint_allows_credentials(endpoint) is expected


def test_execution_and_assurance_modules_do_not_import_discovery_services():
    guarded = ("compiler.py", "runner.py", "golden.py", "reconcile.py")
    forbidden_roots = {
        "embeddings",
        "retrieval",
        "investigation",
        "agents",
        "process_capture",
    }
    violations = []

    for filename in guarded:
        tree = ast.parse((SOURCE / filename).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".")[0]
                if root in forbidden_roots:
                    violations.append(f"{filename}: from {module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name.startswith("sematik."):
                        root = name.split(".")[1]
                        if root in forbidden_roots:
                            violations.append(f"{filename}: import {name}")

    assert violations == []
