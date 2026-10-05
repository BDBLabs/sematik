"""End-to-end proof of the core semantic lifecycle (spec §73, minimal):
profile → hypotheses → approved mapping → compile → execute →
backward lineage → reconciliation → manifest."""

import json
import pathlib

import pytest

from sematik.compiler import PlanStep, compile_mapping
from sematik.discovery import hypotheses_for_column, profile_column
from sematik.mapping import Mapping
from sematik.model import Confidence
from sematik.reconcile import population_reconcile
from sematik.runner import run_conversion

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "legacy_parcels.json"


def _rows():
    return json.loads(FIXTURE.read_text())["rows"]


def test_discovery_profiles_source():
    profile = profile_column([r["APN"] for r in _rows()])
    hyps = hypotheses_for_column("APN", profile)
    assert any("identifier" in h.concept for h in hyps)
    assert profile["distinct_ratio"] == 1.0


def test_lifecycle_end_to_end():
    rows = _rows()
    apn_profile = profile_column([r["APN"] for r in rows])
    assert apn_profile["distinct"] == 4

    # Canonical mapping: legacy parcel fields → canonical assessment total.
    mapping = Mapping(
        source_artifact="LEGACYDB.PARCEL",
        canonical_concept="Assessment.Valuation[type=LAND+IMP].total",
        target_artifact="total_assessed",
        confidence=Confidence(0.9, ("domain-rule", "reconciliation")),
        rule_refs=["RTC-110"],
        domain_pack="cpasf@0.1.0",
        approved_by="test",
        approval_ref="review-2026-10-05",
        version="0.1.0",
    )
    mapping.add_level(1, "physical", "LNDVAL+AV_IMP → staging.total_assessed")
    mapping.add_level(2, "semantic", "LNDVAL/AV_IMP → assessed value components")
    mapping.add_level(3, "canonical", "Assessment.Valuation.total")
    mapping.add_level(4, "context", "roll_type=REGULAR")
    mapping.add_level(5, "temporal", "applies to represented roll period")
    mapping.add_level(6, "authority", "RTC-110 + assessor enrollment record")
    mapping.add_level(7, "target", "total_assessed numeric")
    assert mapping.complete() and mapping.approved()

    steps = [
        PlanStep("derive_sum", {"parts": ["LNDVAL", "AV_IMP"], "to": "total_assessed"}),
        PlanStep("copy", {"from": "APN", "to": "apn"}),
        PlanStep("code_translate", {"from": "XFER", "to": "transfer_kind",
                                     "table": {"REG": "regular", "PT": "partial"}}),
        PlanStep("assert_not_null", {"field": "APN"}),
    ]
    plan = compile_mapping(mapping, steps)
    run = run_conversion(rows, plan, mapping,
                         source_snapshot="fixture-legacy-2026-10-05",
                         domain_pack_version="cpasf@0.1.0", engine_version="0.0.1",
                         provenance_of=lambda r: None)

    # 3 known transfer kinds convert; UNK9 row is rejected, never coerced (§68).
    assert run.converted == 3 and run.rejected == 1
    assert run.exceptions[0].reason.find("UNK9") > 0

    # backward lineage: assertions built from converted rows carry the plan's
    # mapping digest in transformation_history (§21).
    from sematik.compiler import assertion_from_plan_output
    from sematik.model import Provenance
    a = assertion_from_plan_output(plan, run.outputs[0],
                                   Provenance(source_system="legacy-cama",
                                              source_table="PARCEL",
                                              source_record="r1"), mapping)
    assert plan.mapping_digest in a.transformation_history

    # reconciliation: every APN accounted except the one rejected row.
    recon = population_reconcile(rows, run.outputs, source_key="APN", target_key="apn")
    assert recon["missing_in_target"] == ["001-004"]
    assert recon["balanced"] is False

    # reproducibility: identical inputs + versions ⇒ identical manifest hash.
    run2 = run_conversion(rows, compile_mapping(mapping, steps), mapping,
                          source_snapshot="fixture-legacy-2026-10-05",
                          domain_pack_version="cpasf@0.1.0", engine_version="0.0.1",
                          provenance_of=lambda r: None)
    assert run.manifest_hash() == run2.manifest_hash()
