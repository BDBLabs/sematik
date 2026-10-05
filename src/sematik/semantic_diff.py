"""Semantic diff — compare two mapping-model versions by *meaning*, not by
JSON lines (spec §60)."""

from __future__ import annotations

from dataclasses import asdict

from .mapping import Mapping


def semantic_diff(old: Mapping, new: Mapping) -> dict[str, object]:
    changes: list[str] = []
    if old.canonical_concept != new.canonical_concept:
        changes.append(f"canonical concept changed: {old.canonical_concept!r} → {new.canonical_concept!r}")
    if old.source_artifact != new.source_artifact:
        changes.append(f"source artifact changed: {old.source_artifact!r} → {new.source_artifact!r}")
    if old.target_artifact != new.target_artifact:
        changes.append(f"target artifact changed: {old.target_artifact!r} → {new.target_artifact!r}")
    if old.confidence.overall != new.confidence.overall:
        changes.append(f"confidence {old.confidence.overall} → {new.confidence.overall}")
    if sorted(old.rule_refs) != sorted(new.rule_refs):
        changes.append(f"rules {sorted(old.rule_refs)} → {sorted(new.rule_refs)}")
    old_lv = {l.level: l.statement for l in old.levels}
    new_lv = {l.level: l.statement for l in new.levels}
    for level in sorted(set(old_lv) | set(new_lv)):
        if old_lv.get(level) != new_lv.get(level):
            changes.append(f"level {level} statement: {old_lv.get(level)!r} → {new_lv.get(level)!r}")
    return {"mapping": new.id, "old_digest": old.digest(), "new_digest": new.digest(),
            "meaning_changed": bool(changes), "changes": changes}
