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
        invariants=CPASF_INVARIANTS,
        known_patterns=["CAMA ROLL_PRINT", "PARCEL+AV_LAND+AV_IMP layout", "XFER_TYPE 0-7 enumeration"],
    )
    return pack


def every_assessment_references_appraised_unit(assertions) -> bool:
    """Invariant (spec §32 example): every enrolled assessment references an
    appraisal unit."""
    cs = [a.concept for a in assertions]
    return not ("Assessment" in cs and "Property" not in cs)


def derived_values_identify_inputs(assertions) -> bool:
    """Invariant: a derived value must identify its inputs (spec §32)."""
    from .model import DerivationStatus
    return all(a.derivation != DerivationStatus.DERIVED_VALUE
               or a.transformation_history for a in assertions)


def target_from_legacy_retains_lineage(assertions) -> bool:
    """Invariant: a target object created from legacy information must retain
    source lineage (spec §32)."""
    from .model import DerivationStatus
    return all(a.derivation != DerivationStatus.DERIVED_VALUE
               or (a.provenance.source_system and a.transformation_history)
               for a in assertions)


CPASF_INVARIANTS = [
    ("Assessment references an appraisal unit", every_assessment_references_appraised_unit),
    ("Derived value identifies its inputs", derived_values_identify_inputs),
    ("Target object retains source lineage", target_from_legacy_retains_lineage),
]
