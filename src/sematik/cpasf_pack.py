"""CPASF Domain Pack — the first demanding pack (spec §56).

Generic engine stays domain-agnostic; this module supplies CPASF vocabulary,
code sets, rules, and example invariants as *data*, not engine logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .domain_pack import CodeSet, DomainPack


CPASF_CONCEPTS: dict[str, str] = {
    "Property": "A parcel or property interest with a durable identity",
    "PropertyInterest": "An ownership/appraisal interest subordinate to a property",
    "Assessment": "A taxable conclusion for a property interest for a period",
    "Valuation": "A valued component (land, improvements, exemptions) of an assessment",
    "RollTransaction": "Regular, supplemental, escape, or other roll action",
    "BaseYearComponent": "Base-year value component tracked for Prop 13 purposes",
    "Exemption": "An exclusion reducing taxable value, with its own effective period",
    "Transfer": "A change of ownership or other transfer event",
    "Appeal": "A contest of an assessed conclusion",
    "Correction": "A post-certification restatement of a published state",
    "ValuationEvidence": "Documentary evidence supporting a valuation conclusion",
}


CPASF_CODE_SETS: dict[str, dict[str, str]] = {
    "roll_type": {"REG": "regular", "SUP": "supplemental", "ESC": "escape", "PND": "pending"},
    "taxability_state": {"TAX": "taxable", "EXM": "exempt", "PRT": "partially_taxable"},
    "transfer_kind": {"REG": "regular", "PT": "partial", "FULL": "full", "NONE": "none"},
    "ownership_state": {"OWN": "owner", "TEN": "tenant_in_common", "JT": "joint_tenancy", "TR": "trust"},
}


def cpasf_pack(version: str = "0.1.0") -> DomainPack:
    code_sets = {
        name: CodeSet(name=name, mappings=mappings)
        for name, mappings in CPASF_CODE_SETS.items()
    }
    pack = DomainPack(
        name="cpasf",
        version=version,
        canonical_concepts=CPASF_CONCEPTS,
        code_sets=code_sets,
        known_patterns=["CAMA ROLL_PRINT", "PARCEL+AV_LAND+AV_IMP layout", "XFER_TYPE 0-7 enumeration"],
    )
    return pack


def assessment_has_appraised_unit(assertions) -> bool:
    concepts = {a.concept for a in assertions}
    return "Assessment" in concepts and any(c.startswith("ValuationEvidence") or c == "Property" for c in concepts)
