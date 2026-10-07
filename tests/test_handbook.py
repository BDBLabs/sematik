"""Handbook corpus loader: packet parsing, digests, provisional flags."""

import pathlib

from sematik.handbook import load_handbook_corpus, parse_packet

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "handbook"


def test_packet_header_and_item_parsed():
    passages = parse_packet(FIXTURES / "PACKET_T.md")
    by_id = {p.item_id: p for p in passages}
    assert "" in by_id  # packet-level record
    item = by_id["PB-TST-01"]
    assert item.packet_id.startswith("T")
    assert "RTC §000" in item.authority
    assert "AH000 Ch 1" in item.guidance
    assert item.provisional is True
    assert len(item.content_digest) == 64


def test_reviewed_packet_is_not_provisional():
    passages = parse_packet(FIXTURES / "PACKET_U.md")
    assert all(p.provisional is False for p in passages)


def test_corpus_loads_directory_and_cites():
    passages = load_handbook_corpus(FIXTURES)
    ids = {p.item_id for p in passages}
    assert {"PB-TST-01", "PB-TST-02"} <= ids
    cite = next(p for p in passages if p.item_id == "PB-TST-02").cite()
    assert "PB-TST-02" in cite and "provisional" not in cite
    prov = next(p for p in passages if p.item_id == "PB-TST-01").cite()
    assert "provisional" in prov


def test_digests_stable_across_loads():
    first = {p.item_id: p.content_digest for p in load_handbook_corpus(FIXTURES)}
    second = {p.item_id: p.content_digest for p in load_handbook_corpus(FIXTURES)}
    assert first == second
