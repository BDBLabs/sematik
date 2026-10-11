"""sematik web API — FastAPI backend wrapping the semantic conversion engine.

Exposes the full §73 lifecycle: profile -> hypothesis -> compile -> execute ->
reconcile -> entropy -> lineage -> manifest.  Deployed to Railway; frontend
served from the same container via static mount.

Run locally:  uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sematik.compiler import (
    CompilationError,
    PlanStep,
    compile_mapping,
    compile_mapping_to_sql,
)
from sematik.discovery import (
    candidate_relationships,
    hypotheses_for_column,
    profile_column,
)
from sematik.entropy import (
    UncalibratedConfidence,
    concept_entropy,
    semantic_entropy,
    semantic_entropy_flagged,
)
from sematik.mapping import Mapping
from sematik.model import Confidence, Provenance, SemanticHypothesis
from sematik.reconcile import (
    population_reconcile,
    semantic_reconcile,
)
from sematik.runner import run_conversion

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# ---------------------------------------------------------------------------
# Pydantic DTOs
# ---------------------------------------------------------------------------


class ColumnData(BaseModel):
    """A column to profile / generate hypotheses for."""

    name: str
    values: list[Any]


class LevelIn(BaseModel):
    level: int
    kind: str
    statement: str
    context: dict[str, Any] = Field(default_factory=dict)


class MappingIn(BaseModel):
    """JSON representation of a Mapping (spec §13 seven levels)."""

    source_artifact: str
    canonical_concept: str
    target_artifact: str = ""
    levels: list[LevelIn] = Field(default_factory=list)
    confidence: dict[str, Any] = Field(default_factory=lambda: {"overall": 1.0})
    rule_refs: list[str] = Field(default_factory=list)
    domain_pack: str = ""
    approved_by: str = ""
    approval_ref: str = ""
    version: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_question_ids: list[str] = Field(default_factory=list)
    golden_plan_digest: str = ""
    id: str | None = None  # override the UUID-generated id (for testing)


class StepIn(BaseModel):
    op: str
    args: dict[str, Any] = Field(default_factory=dict)


class HypothesisIn(BaseModel):
    candidate_meaning: str
    concept: str
    confidence: dict[str, Any]
    supporting: list[str] = Field(default_factory=list)
    contradicting: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    affected_records: int = 0
    evidence_basis: str = ""


class ExecutionPayload(BaseModel):
    mapping: MappingIn
    steps: list[StepIn]
    rows: list[dict[str, Any]]
    source_snapshot: str = "api-run"
    domain_pack_version: str = "cpasf@0.1.0"
    golden: list[dict[str, Any]] | None = None
    require_golden: bool = False


class TableData(BaseModel):
    """Rows grouped by table name for candidate-relationship discovery."""

    tables: dict[str, list[dict[str, Any]]]


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

_RECONCILE_FIELDS = {"source_key", "target_key", "numeric_pairs"}


def _to_mapping(m: MappingIn) -> Mapping:
    """Build a Mapping object from the API DTO."""
    conf = m.confidence
    confidence = Confidence(
        overall=conf.get("overall", 1.0),
        drivers=tuple(conf.get("drivers", ())),
        calibrated=conf.get("calibrated", True),
    )
    mapping = Mapping(
        source_artifact=m.source_artifact,
        canonical_concept=m.canonical_concept,
        target_artifact=m.target_artifact,
        confidence=confidence,
        rule_refs=list(m.rule_refs),
        domain_pack=m.domain_pack,
        approved_by=m.approved_by,
        approval_ref=m.approval_ref,
        version=m.version,
        evidence_refs=list(m.evidence_refs),
        blocking_question_ids=list(m.blocking_question_ids),
        golden_plan_digest=m.golden_plan_digest,
    )
    for lv in m.levels:
        mapping.add_level(lv.level, lv.kind, lv.statement, **lv.context)
    if m.id is not None:
        mapping.id = m.id
    return mapping


def _to_step(s: StepIn) -> PlanStep:
    return PlanStep(s.op, s.args)


def _to_hypotheses(hs: list[HypothesisIn]) -> list[SemanticHypothesis]:
    """Deserialize API hypotheses into SemanticHypothesis objects."""
    result: list[SemanticHypothesis] = []
    for h in hs:
        c = h.confidence
        confidence = Confidence(
            overall=c.get("overall", 0.5),
            drivers=tuple(c.get("drivers", ())),
            calibrated=c.get("calibrated", True),
        )
        result.append(SemanticHypothesis(
            candidate_meaning=h.candidate_meaning,
            concept=h.concept,
            confidence=confidence,
            evidence_basis=h.evidence_basis,
            supporting=list(h.supporting),
            contradicting=list(h.contradicting),
            alternatives=list(h.alternatives),
            affected_records=h.affected_records,
        ))
    return result


def _serialize_hypotheses(hyps: list[SemanticHypothesis]) -> list[dict[str, Any]]:
    """Convert SemanticHypothesis objects to JSON-safe dicts."""
    out = []
    for h in hyps:
        out.append({
            "candidate_meaning": h.candidate_meaning,
            "concept": h.concept,
            "confidence": {
                "overall": h.confidence.overall,
                "drivers": list(h.confidence.drivers),
                "calibrated": h.confidence.calibrated,
            },
            "evidence_basis": h.evidence_basis,
            "supporting": list(h.supporting),
            "contradicting": list(h.contradicting),
            "alternatives": list(h.alternatives),
            "affected_records": h.affected_records,
        })
    return out


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="sematik API",
    description="Semantic Conversion Engine — meaning-based data conversion "
                "over the Semantic Intermediate Representation (§19/§73).",
    version="0.0.1",
)

# Allow frontend dev server + Railway static mount to coexist.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened to explicit origins in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sematik", "version": "0.0.1"}


# ---------------------------------------------------------------------------
# Discovery plane — profile → hypothesis → candidate relationships
# ---------------------------------------------------------------------------

@app.post("/api/v1/profile")
def profile(data: ColumnData) -> dict[str, Any]:
    """Profile a single column from raw values (spec §5)."""
    return profile_column(data.values)


@app.post("/api/v1/hypotheses")
def hypotheses(data: ColumnData) -> list[dict[str, Any]]:
    """Generate discovery hypotheses for a profiled column.

    Returns hypotheses with ordinal evidence strength (uncalibrated) and
    a stated ``evidence_basis`` (#36).  See also ``/api/v1/entropy/semantic``
    to compute entropy over these hypotheses.
    """
    prof = profile_column(data.values)
    return _serialize_hypotheses(hypotheses_for_column(data.name, prof))


@app.post("/api/v1/candidates")
def candidates(data: TableData) -> list[dict[str, Any]]:
    """Heuristic FK-like candidate relationships (spec §12, issue #37).

    Uses ``min_cardinality=3`` to suppress spurious matches between
    low-cardinality columns (booleans, flags, status codes)."""
    rels = candidate_relationships(data.tables)
    # Serialize Confidence objects to dicts for JSON.
    for r in rels:
        if isinstance(r.get("confidence"), Confidence):
            r["confidence"] = {
                "overall": r["confidence"].overall,
                "drivers": list(r["confidence"].drivers),
                "calibrated": r["confidence"].calibrated,
            }
    return rels


# ---------------------------------------------------------------------------
# Compilation plane — approve → compile → SQL
# ---------------------------------------------------------------------------

@app.post("/api/v1/mapping/digest")
def mapping_digest(m: MappingIn) -> dict[str, Any]:
    """Compute a mapping's digest, completeness, and approval status."""
    mapping = _to_mapping(m)
    return {
        "digest": mapping.digest(),
        "complete": mapping.complete(),
        "approved": mapping.approved(),
        "approval_problems": mapping.approval_problems(),
    }


@app.post("/api/v1/compile")
def compile(mapping: MappingIn, steps: list[StepIn]) -> dict[str, Any]:
    """Compile an approved Mapping + steps into an executable TransformationPlan."""
    m = _to_mapping(mapping)
    try:
        plan = compile_mapping(m, [_to_step(s) for s in steps])
    except CompilationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "plan_digest": plan.digest(),
        "target_artifact": plan.target_artifact,
        "mapping_digest": plan.mapping_digest,
        "steps": [{"op": s.op, "args": dict(s.args)} for s in plan.steps],
    }


@app.post("/api/v1/compile-sql")
def compile_sql(mapping: MappingIn, steps: list[StepIn],
                source_table: str = Body(...),
                dialect: str = Body("postgres")) -> dict[str, Any]:
    """Lower a plan to an equivalent SQL SELECT (spec §19, issue #30).

    Fail-closed: ``code_translate`` and ``assert_not_null`` have no safe
    single-SELECT lowering and are refused.  SQL comment fields are
    sanitized to prevent injection (#30 HIGH follow-up)."""
    m = _to_mapping(mapping)
    try:
        sql = compile_mapping_to_sql(
            m, [_to_step(s) for s in steps], source_table=source_table,
            dialect=dialect,
        )
    except CompilationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"sql": sql}


# ---------------------------------------------------------------------------
# Execution plane — execute → reconcile → manifest
# ---------------------------------------------------------------------------

@app.post("/api/v1/execute")
def execute(payload: ExecutionPayload) -> dict[str, Any]:
    """Run a compiled plan over source rows (spec §29/§30)."""
    m = _to_mapping(payload.mapping)
    steps = [_to_step(s) for s in payload.steps]
    try:
        plan = compile_mapping(m, steps)
    except CompilationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        run = run_conversion(
            payload.rows, plan, m,
            source_snapshot=payload.source_snapshot,
            domain_pack_version=payload.domain_pack_version,
            engine_version="0.0.1",
            provenance_of=lambda r: Provenance(
                source_system="api", source_record=str(r.get("_id", "?"))),
            golden=payload.golden,
            require_golden=payload.require_golden,
        )
    except CompilationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "converted": run.converted,
        "rejected": run.rejected,
        "total": run.total_records,
        "outputs": run.outputs,
        "exceptions": [vars(e) for e in run.exceptions],
        "assertions": [
            {"concept": a.concept, "value": a.value,
             "source": a.provenance.ref(),
             "history": list(a.transformation_history)}
            for a in run.assertions
        ],
        "manifest_hash": run.manifest_hash(),
        "plan_digest": plan.digest(),
    }


@app.post("/api/v1/reconcile/population")
def reconcile_population(rows: list[dict[str, Any]],
                         outputs: list[dict[str, Any]],
                         source_key: str = Body(...),
                         target_key: str = Body(...)) -> dict[str, Any]:
    return population_reconcile(
        rows, outputs, source_key=source_key, target_key=target_key)


@app.post("/api/v1/reconcile/records")
def reconcile_records(rows: list[dict[str, Any]],
                      outputs: list[dict[str, Any]],
                      source_key: str = Body(...),
                      target_key: str = Body(...),
                      numeric_pairs: list[list[str]] = Body(...)) -> dict[str, Any]:  # noqa: B008
    from sematik.reconcile import reconcile_records as _rec
    return _rec(rows, outputs,
                source_key=source_key, target_key=target_key,
                numeric_pairs=[tuple(p) for p in numeric_pairs])


@app.post("/api/v1/reconcile/semantic")
def reconcile_semantic(assertions: list[dict[str, Any]],
                       invariants: list[list[str]] | None = None) -> dict[str, Any]:
    """Run semantic invariants (§29). Optionally pass custom invariants
    as [description, condition-name] pairs; defaults to CPASF invariants."""
    from sematik.cpasf_pack import CPASF_INVARIANTS
    from sematik.model import Assertion, DerivationStatus, Provenance

    if invariants is None:
        inv = CPASF_INVARIANTS
    else:
        # Build invariants from [description, kind] pairs.
        # This is a simplified path for ad-hoc testing.
        raise HTTPException(
            400, "custom invariants not supported; use default CPASF invariants "
                 "(omit 'invariants' field).")
    asrt_objs = []
    for a in assertions:
        asrt_objs.append(Assertion(
            concept=a["concept"], value=a["value"],
            derivation=DerivationStatus(a.get("derivation", "observed_fact")),
            provenance=Provenance(source_system=a.get("source_system", "")),
        ))
    return semantic_reconcile(asrt_objs, inv)


# ---------------------------------------------------------------------------
# Entropy plane — §76
# ---------------------------------------------------------------------------

@app.post("/api/v1/entropy/concept")
def concept_entropy_endpoint(hypotheses: list[HypothesisIn]) -> dict[str, Any]:
    """Per-concept entropy over competing hypotheses (§76).

    Refuses uncalibrated confidences — returns 422 with an explanation.
    Use /api/v1/entropy/semantic-flagged for a best-effort score."""
    try:
        hyps = _to_hypotheses(hypotheses)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return {"entropy": concept_entropy(hyps)}
    except UncalibratedConfidence as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/entropy/semantic")
def semantic_entropy_endpoint(hypotheses: list[HypothesisIn]) -> dict[str, Any]:
    """Weighted-mean semantic entropy across concepts (§76).

    Raises 422 if any hypothesis is uncalibrated (#36)."""
    try:
        hyps = _to_hypotheses(hypotheses)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return {"entropy": semantic_entropy(hyps)}
    except UncalibratedConfidence as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/entropy/semantic-flagged")
def semantic_entropy_flagged_endpoint(hypotheses: list[HypothesisIn]) -> dict[str, Any]:
    """Best-effort semantic entropy with warnings for uncalibrated inputs (#36).

    Never raises — returns a numeric score plus a list of warning strings."""
    try:
        hyps = _to_hypotheses(hypotheses)
    except ValueError as exc:
        return {"entropy": None, "warnings": [str(exc)]}
    score, warnings = semantic_entropy_flagged(hyps)
    return {"entropy": score, "warnings": warnings}


# ---------------------------------------------------------------------------
# Fixtures — convenient seed data for the UI
# ---------------------------------------------------------------------------

@app.get("/api/v1/fixture/legacy_parcels")
def fixture_legacy_parcels() -> list[dict[str, Any]]:
    """The demo fixture: California legacy parcel assessments (4 rows)."""
    path = FIXTURE_DIR / "legacy_parcels.json"
    return json.loads(path.read_text()).get("rows", [])


@app.get("/api/v1/fixture/demo-mapping")
def fixture_demo_mapping() -> dict[str, Any]:
    """A fully-approved demo Mapping (mirrors demo.py) for UI prefilling."""
    return {
        "source_artifact": "LEGACYDB.PARCEL",
        "canonical_concept": "Assessment.Valuation[type=LAND+IMP].total",
        "target_artifact": "total_assessed",
        "confidence": {"overall": 0.9, "drivers": ["domain-rule", "reconciliation"],
                       "calibrated": True},
        "rule_refs": ["RTC-110"],
        "domain_pack": "cpasf@0.1.0",
        "approved_by": "demo-operator",
        "approval_ref": "demo-approval",
        "version": "0.1.0",
        "evidence_refs": ["handbook:parcel-assessment-rules",
                          "court-record:enrollment-2026"],
        "golden_plan_digest": "golden:fixture-golden-plan",
        "levels": [
            {"level": 1, "kind": "physical",
             "statement": "LNDVAL+AV_IMP → staging.total_assessed"},
            {"level": 2, "kind": "semantic",
             "statement": "LNDVAL/AV_IMP → assessed value components"},
            {"level": 3, "kind": "canonical",
             "statement": "Assessment.Valuation.total"},
            {"level": 4, "kind": "context",
             "statement": "roll_type=REGULAR"},
            {"level": 5, "kind": "temporal",
             "statement": "applies to represented roll period"},
            {"level": 6, "kind": "authority",
             "statement": "RTC-110 + assessor enrollment record"},
            {"level": 7, "kind": "target",
             "statement": "total_assessed numeric"},
        ],
    }


@app.get("/api/v1/fixture/demo-steps")
def fixture_demo_steps() -> list[dict[str, Any]]:
    """Demo compilation plan steps."""
    return [
        {"op": "derive_sum", "args": {"parts": ["LNDVAL", "AV_IMP"], "to": "total_assessed"}},
        {"op": "copy", "args": {"from": "APN", "to": "apn"}},
        {"op": "code_translate", "args": {"from": "XFER", "to": "transfer_kind",
                                          "table": {"REG": "regular", "PT": "partial"}}},
    ]


# ---------------------------------------------------------------------------
# Frontend static mount (built React app, served from same container)
# ---------------------------------------------------------------------------

UI_STATIC = pathlib.Path(__file__).resolve().parent.parent / "ui" / "dist"
if UI_STATIC.exists():
    app.mount("/", StaticFiles(directory=str(UI_STATIC), html=True), name="ui")
