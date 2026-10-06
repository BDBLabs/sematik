"""Conversion runner — deterministic execution, exceptions, reconciliation
into a Conversion Run (spec §29/§30/§36).

Fail-closed: a run refuses an unapproved mapping or a plan that is no longer
bound to it; every converted record must carry source provenance and yields a
lineage assertion on the real execution path; every record ends up either
converted or rejected-with-reason (``converted + rejected == total``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from .compiler import (
    CompilationError,
    ConversionUngecognizable,
    LineageError,
    TransformationPlan,
    assertion_from_plan_output,
)
from .mapping import Mapping
from .model import Assertion, Provenance


def _digest(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class RunException:
    record_id: str
    reason: str
    phase: str
    provenance_ref: str = ""


@dataclass
class ConversionRun:
    source_snapshot: str
    mapping_version: str
    domain_pack_version: str
    engine_version: str
    plan_digest: str = ""
    source_digest: str = ""
    total_records: int = 0
    converted: int = 0
    rejected: int = 0
    exceptions: list[RunException] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    golden: dict[str, Any] | None = None

    def manifest_hash(self) -> str:
        """Content-bound manifest: covers the executed plan, the source rows
        actually read, every output, every exception and every lineage
        assertion — not merely run metadata and counts (#25)."""
        payload = {
            "snapshot": self.source_snapshot, "mapping": self.mapping_version,
            "pack": self.domain_pack_version, "engine": self.engine_version,
            "plan": self.plan_digest, "source": self.source_digest,
            "total": self.total_records, "converted": self.converted,
            "rejected": self.rejected,
            "outputs": _digest(self.outputs),
            "exceptions": _digest([vars(e) for e in self.exceptions]),
            "assertions": _digest([a.fingerprint() for a in self.assertions]),
            "golden_ok": None if self.golden is None else self.golden.get("ok"),
        }
        return _digest(payload)


def _enforce_golden_gate(plan: TransformationPlan,
                         golden: list[dict[str, Any]] | None) -> None:
    """Fail the run before any conversion if required regression evidence
    is missing, empty, or failing (spec §61)."""
    if not golden:
        raise CompilationError(
            "require_golden is set but no golden records were supplied; "
            "refusing to convert without required regression evidence")
    from .golden import run_golden_records
    gate = run_golden_records(plan, golden)
    if not gate["ok"]:
        raise CompilationError(
            "golden regression failed before conversion; refusing to run: "
            + "; ".join(f["name"] for f in gate["failures"]))


def run_conversion(rows: Iterable[dict[str, Any]], plan: TransformationPlan,
                   mapping: Mapping, *, source_snapshot: str,
                   domain_pack_version: str, engine_version: str,
                   provenance_of: Callable[[dict[str, Any]], Provenance | None],
                   golden: list[dict[str, Any]] | None = None,
                   require_golden: bool = False) -> ConversionRun:
    problems = mapping.approval_problems()
    if problems:
        raise CompilationError("cannot run an unapproved mapping: " + "; ".join(problems))
    if not plan.bound_to(mapping):
        raise CompilationError(
            "plan is not bound to the current approved mapping "
            "(mapping or approval changed after compilation); recompile and re-approve")
    if not callable(provenance_of):
        raise CompilationError(
            "provenance_of is required: every converted record must carry source lineage")
    if require_golden:
        # The exact immutable plan proves itself against required evidence
        # BEFORE any source row converts — a failing anchor means the
        # mapping changed meaning, and converting anyway would launder it.
        _enforce_golden_gate(plan, golden)

    run = ConversionRun(
        source_snapshot=source_snapshot,
        mapping_version=mapping.digest(),
        domain_pack_version=domain_pack_version,
        engine_version=engine_version,
        plan_digest=plan.digest(),
    )
    source_hash = hashlib.sha256()

    def reject(
        record_id: str,
        reason: str,
        phase: str,
        provenance: Provenance | None = None,
    ) -> None:
        run.rejected += 1
        run.exceptions.append(
            RunException(
                record_id=record_id,
                reason=reason,
                phase=phase,
                provenance_ref="" if provenance is None else provenance.ref(),
            )
        )

    for row in rows:
        run.total_records += 1
        source_hash.update(json.dumps(row, sort_keys=True, default=str).encode() + b"\n")
        if not isinstance(row, dict):
            reject("?", f"record is {type(row).__name__}, not a mapping", "input")
            continue
        rid = str(row.get("_id", "?"))
        try:
            provenance = provenance_of(row)
        except Exception as e:
            reject(rid, f"provenance lookup failed: {type(e).__name__}", "lineage")
            continue
        if (
            not isinstance(provenance, Provenance)
            or not provenance.source_system
            or not provenance.source_record
        ):
            reject(
                rid,
                "record-level source provenance is required; "
                "source_system and source_record must both be present",
                "lineage",
                provenance if isinstance(provenance, Provenance) else None,
            )
            continue
        try:
            out = plan.execute(row)
        except ConversionUngecognizable as e:
            reject(rid, str(e), "execution", provenance)
            continue
        except CompilationError:
            raise  # a defective plan is not a bad record — fail the run loudly
        except Exception as e:  # unexpected data shape: reject the record, keep the batch
            reject(
                rid,
                f"unexpected {type(e).__name__}: {str(e)[:200]}",
                "execution",
                provenance,
            )
            continue
        try:
            assertion = assertion_from_plan_output(plan, out, provenance, mapping)
        except LineageError as e:
            reject(rid, str(e), "lineage", provenance)
            continue
        run.outputs.append(out)
        run.assertions.append(assertion)
        run.converted += 1

    run.source_digest = source_hash.hexdigest()
    if run.converted + run.rejected != run.total_records:
        raise RuntimeError("run accounting invariant violated: "
                           "converted + rejected != total_records")
    if golden is not None:
        from .golden import run_golden_records
        # With require_golden the same evidence already gated this run
        # above; re-running keeps the recorded result identical to the gate.
        run.golden = run_golden_records(plan, golden)
    return run
