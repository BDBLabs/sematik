"""Conversion runner — deterministic execution, exceptions, reconciliation
into a Conversion Run (spec §29/§30/§36)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .compiler import CompilationError, ConversionUngecognizable, TransformationPlan
from .mapping import Mapping
from .model import Assertion, Provenance


@dataclass
class RunException:
    record_id: str
    reason: str
    phase: str


@dataclass
class ConversionRun:
    source_snapshot: str
    mapping_version: str
    domain_pack_version: str
    engine_version: str
    total_records: int = 0
    converted: int = 0
    rejected: int = 0
    exceptions: list[RunException] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)

    def manifest_hash(self) -> str:
        payload = json.dumps(
            {"snapshot": self.source_snapshot, "mapping": self.mapping_version,
             "pack": self.domain_pack_version, "engine": self.engine_version,
             "total": self.total_records, "converted": self.converted,
             "rejected": self.rejected}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def run_conversion(rows: Iterable[dict[str, Any]], plan: TransformationPlan,
                   mapping: Mapping, *, source_snapshot: str,
                   domain_pack_version: str, engine_version: str,
                   provenance_of) -> ConversionRun:
    run = ConversionRun(
        source_snapshot=source_snapshot,
        mapping_version=mapping.digest(),
        domain_pack_version=domain_pack_version,
        engine_version=engine_version,
    )
    for row in rows:
        run.total_records += 1
        try:
            out = plan.execute(row)
            run.outputs.append(out)
            run.converted += 1
        except (ConversionUngecognizable, CompilationError) as e:
            run.rejected += 1
            run.exceptions.append(RunException(
                record_id=str(row.get("_id", "?")), reason=str(e), phase="execution"))
            continue
    return run
