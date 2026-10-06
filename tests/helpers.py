"""Shared test builders: a fully approved Mapping and a provenance resolver."""

from sematik.mapping import Mapping
from sematik.model import Confidence, Provenance

_LEVELS = [(1, "physical"), (2, "semantic"), (3, "canonical"), (4, "context"),
           (5, "temporal"), (6, "authority"), (7, "target")]


def approved_mapping(**overrides) -> Mapping:
    fields = dict(source_artifact="s", canonical_concept="c", target_artifact="t",
                  approved_by="reviewer", approval_ref="REVIEW-1", version="1.0.0",
                  confidence=Confidence(0.9))
    fields.update(overrides)
    m = Mapping(**fields)
    for level, kind in _LEVELS:
        m.add_level(level, kind, f"{kind} statement")
    return m


def prov(row):
    return Provenance(source_system="legacy", source_table="T",
                      source_record=str(row.get("_id", "?")))
