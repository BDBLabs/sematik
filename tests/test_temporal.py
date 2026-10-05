from sematik.model import Assertion, TemporalContext
from sematik.temporal import temporal_coverage, temporal_uncertainty_flags
from datetime import date


def test_coverage_counts_dimensions():
    a = Assertion(concept="x", value=1,
                  temporal=TemporalContext(effective_date=date(2026, 1, 1), period="2026"))
    assert temporal_coverage([a]) == {"effective_date": 1, "period": 1}


def test_uncertainty_flag_when_sparse():
    a = Assertion(concept="x", value=1, temporal=TemporalContext(effective_date=date(2026, 1, 1)))
    flags = temporal_uncertainty_flags([a])
    assert len(flags) == 1 and flags[0]["known_dimensions"] == ["effective_date"]
