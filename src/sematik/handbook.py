"""Handbook corpus loader — versioned domain literature as citable evidence.

Assessor handbooks (and their engineered extraction packets) enter the
Domain Pack as corpus content: section identity, version/date, review
status, and content digest travel with every passage, so a mapping can
cite the exact passage behind a decision (spec §6 evidence, §17 packs).

The corpus root is a parameter, never hard-coded: packet files may live
in another repo or move during repo splits. Passages from packets whose
status is not independently reviewed are flagged provisional — usable
as discovery leads, never as authority.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HandbookPassage:
    packet_id: str
    item_id: str          # e.g. "PB-FRM-01"; "" for packet-level records
    title: str
    authority: tuple[str, ...] = ()
    guidance: tuple[str, ...] = ()
    status: str = ""
    method: str = ""
    date: str = ""
    provisional: bool = True
    content_digest: str = ""
    source_path: str = ""

    def cite(self) -> str:
        head = f"{self.packet_id}:{self.item_id}" if self.item_id else self.packet_id
        flag = " (provisional)" if self.provisional else ""
        return f"{head} — {self.title}{flag}".strip(" —")


_HEADER_RE = re.compile(r"^\*\*(Packet|Handbooks|Method|Corpus|Status|Date):\*\*\s*(.*)$")
_ITEM_RE = re.compile(r"^###\s+([A-Z]+-[A-Z]+-\d+)\s+[—–-]\s*(.*)$")
_AUTH_RE = re.compile(r"\*\*Authority:\*\*\s*(.*?)(?=\s*\*\*[A-Z][a-z]*:\*\*|$)")
_GUID_RE = re.compile(r"\*\*Guidance:\*\*\s*(.*?)(?=\s*\*\*[A-Z][a-z]*:\*\*|$)")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_refs(text: str) -> tuple[str, ...]:
    return tuple(p.strip(" .") for p in re.split(r"[;,]", text) if p.strip(" ."))


def parse_packet(path: str | Path) -> list[HandbookPassage]:
    """Parse one extraction packet file into packet + item passages."""
    src = Path(path)
    text = src.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    for line in text.splitlines():
        m = _HEADER_RE.match(line.strip())
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
    packet_id = meta.get("packet", src.stem)
    status = meta.get("status", "")
    lowered = status.lower()
    provisional = not ("independently reviewed" in lowered
                       and "not independently reviewed" not in lowered)
    passages = [
        HandbookPassage(
            packet_id=packet_id,
            item_id="",
            title=f"packet {packet_id} header",
            status=status,
            method=meta.get("method", ""),
            date=meta.get("date", ""),
            provisional=provisional,
            content_digest=_digest(text),
            source_path=str(src),
        )
    ]
    current: dict = {}
    body: list[str] = []

    def flush() -> None:
        if not current:
            return
        content = "\n".join(body).strip()
        passages.append(HandbookPassage(
            packet_id=packet_id,
            item_id=current["id"],
            title=current["title"],
            authority=_split_refs(current.get("authority", "")),
            guidance=_split_refs(current.get("guidance", "")),
            status=status,
            method=meta.get("method", ""),
            date=meta.get("date", ""),
            provisional=provisional,
            content_digest=_digest(current["id"] + "\n" + content),
            source_path=str(src),
        ))

    for line in text.splitlines():
        m = _ITEM_RE.match(line.strip())
        if m:
            flush()
            current = {"id": m.group(1), "title": m.group(2).strip()}
            body = []
            continue
        if current:
            for rx, name in ((_AUTH_RE, "authority"), (_GUID_RE, "guidance")):
                m = rx.search(line)
                if m and name not in current:
                    current[name] = m.group(1).strip()
            body.append(line)
    flush()
    return passages


def load_handbook_corpus(root: str | Path,
                         pattern: str = "*.md") -> list[HandbookPassage]:
    """Load every packet file under root (non-recursive default corpus layout)."""
    passages: list[HandbookPassage] = []
    for path in sorted(Path(root).glob(pattern)):
        if path.is_file():
            passages.extend(parse_packet(path))
    return passages
