"""`python -m sematik.demo` — a visible §73 minimal lifecycle walk:
profile → hypothesis → approved mapping → compile → execute →
backward lineage → reconcile → manifest hash."""

from __future__ import annotations

import json
import pathlib

from .compiler import PlanStep, compile_mapping
from .discovery import hypotheses_for_column, profile_column
from .mapping import Mapping
from .model import Confidence
from .reconcile import population_reconcile, semantic_reconcile
from .cpasf_pack import CPASF_INVARIANTS, cpasf_pack
from .runner import run_conversion

FIXTURE = pathlib.Path(__file__).parent.parent.parent / "tests" / "fixtures" / "legacy_parcels.json"


def main() -> None:
    rows = json.loads(FIXTURE.read_text())["rows"]
    print(f"[1] Loaded {len(rows)} source rows from {FIXTURE.name}")

    apn_profile = profile_column([r["APN"] for r in rows])
    print(f"[2] APN profile: distinct/{apn_profile['count']}, null_rate={apn_profile['null_rate']}")
    for h in hypotheses_for_column("APN", apn_profile):
        print(f"    hypothesis: {h.candidate_meaning} (confidence {h.confidence.overall})")

    mapping = Mapping(
        source_artifact="LEGACYDB.PARCEL",
        canonical_concept="Assessment.Valuation[type=LAND+IMP].total",
        target_artifact="total_assessed",
        confidence=Confidence(0.9, ("domain-rule", "reconciliation")),
        rule_refs=["RTC-110"], domain_pack="cpasf@0.1.0",
        approved_by="demo-operator", approval_ref="demo", version="0.1.0",
    )
    for lv, kind, stmt in [
        (1, "physical", "LNDVAL+AV_IMP → staging.total_assessed"),
        (2, "semantic", "LNDVAL/AV_IMP → assessed value components"),
        (3, "canonical", "Assessment.Valuation.total"),
        (4, "context",   "roll_type=REGULAR"),
        (5, "temporal",  "applies to represented roll period"),
        (6, "authority", "RTC-110 + assessor enrollment record"),
        (7, "target",    "total_assessed numeric"),
    ]:
        mapping.add_level(lv, kind, stmt)
    print(f"[3] Mapping complete={mapping.complete()}, approved={mapping.approved()}, digest={mapping.digest()}")

    steps = [
        PlanStep("derive_sum", {"parts": ["LNDVAL", "AV_IMP"], "to": "total_assessed"}),
        PlanStep("copy", {"from": "APN", "to": "apn"}),
        PlanStep("code_translate", {"from": "XFER", "to": "transfer_kind",
                                     "table": {"REG": "regular", "PT": "partial"}}),
    ]
    plan = compile_mapping(mapping, steps)
    run = run_conversion(rows, plan, mapping,
                         source_snapshot="demo-fixture-2026-10-05",
                         domain_pack_version="cpasf@0.1.0", engine_version="0.0.1",
                         provenance_of=lambda r: None)
    print(f"[4] Conversion: {run.converted} converted, {run.rejected} rejected (fail-closed on XFER=UNK9)")
    for e in run.exceptions:
        print(f"    exception: {e.record_id} → {e.reason}")

    recon = population_reconcile(rows, run.outputs, source_key="APN", target_key="apn")
    print(f"[5] Population reconciliation: missing_in_target={recon['missing_in_target']}, balanced={recon['balanced']}")

    from .model import Assertion, DerivationStatus, Provenance
    asserts = [
        Assertion(concept="Assessment", value=1,
                  transformation_history=("x",), provenance=Provenance(source_system="legacy")),
        Assertion(concept="Property", value=1, provenance=Provenance(source_system="legacy")),
    ]
    inv = semantic_reconcile(asserts, CPASF_INVARIANTS)
    print(f"[6] Invariants checked={inv['invariants_checked']}, failures={inv['failures']}")
    print(f"[7] Conversion manifest hash: {run.manifest_hash()}")


if __name__ == "__main__":
    main()
