"""Record-level semantic confidence (§83): a mapping can be 99.8% reliable
while an individual record is outlier-unusual. Flag those records."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def record_confidence(rows: Iterable[dict[str, Any]], key_fields: list[str]) -> list[dict[str, Any]]:
    combo_counts = Counter()
    keyed = []
    for r in rows:
        combo = tuple(str(r.get(k)) for k in key_fields)
        combo_counts[combo] += 1
        keyed.append((r, combo))
    total = sum(combo_counts.values())
    out = []
    for r, combo in keyed:
        freq = combo_counts[combo] / total
        flagged = freq < 0.01 and combo_counts[combo] == 1
        out.append({"record": r, "combo_frequency": freq,
                    "record_confidence": round(freq, 6), "outlier": flagged})
    return out
