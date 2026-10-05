from sematik.evidence import EvidenceGraph, EdgeRel


def test_round_trip_provenance():
    g = EvidenceGraph()
    g.add_node("PARCEL.AV_LAND", "field")
    g.add_node("AssessmentValueComponent", "concept")
    g.link("PARCEL.AV_LAND", EdgeRel.MAPS_TO, "AssessmentValueComponent")
    blob = g.to_json()
    g2 = EvidenceGraph.from_json(blob)
    assert g2.nodes == g.nodes
    assert [(e.src, e.rel, e.dst) for e in g2.edges] == [(e.src, e.rel, e.dst) for e in g.edges]
    assert g2.path_summary("PARCEL.AV_LAND")[0].startswith("PARCEL.AV_LAND")
