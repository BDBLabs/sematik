from sematik.cpasf_pack import (CPASF_INVARIANTS, derived_values_identify_inputs,
                                every_assessment_references_appraised_unit)
from sematik.model import Assertion, Confidence, DerivationStatus, Provenance
from sematik.reconcile import semantic_reconcile


def _assertion(concept, derivation=DerivationStatus.OBSERVED_FACT, history=(), provenance=None):
    return Assertion(concept=concept, value=1, derivation=derivation,
                     transformation_history=history,
                     provenance=provenance or Provenance(source_system="legacy"))


def test_missing_appraisal_unit_flagged():
    bad = [_assertion("Assessment")]
    assert every_assessment_references_appraised_unit(bad) is False
    ok = [_assertion("Assessment"), _assertion("Property")]
    assert every_assessment_references_appraised_unit(ok) is True


def test_derived_value_without_inputs_fails():
    bad = [_assertion("Valuation", DerivationStatus.DERIVED_VALUE, history=())]
    assert derived_values_identify_inputs(bad) is False
    ok = [_assertion("Valuation", DerivationStatus.DERIVED_VALUE, history=("digest123",))]
    assert derived_values_identify_inputs(ok) is True


def test_semantic_reconcile_uses_pack_invariants():
    good = [_assertion("Assessment"), _assertion("Property")]
    report = semantic_reconcile(good, CPASF_INVARIANTS)
    assert report["invariants_checked"] == 3 and report["failures"] == []
