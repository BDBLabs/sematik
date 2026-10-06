"""Semantic diff — compare two mapping-model versions by *meaning*, not by
JSON lines (spec §60)."""

from __future__ import annotations

from .mapping import Mapping, MappingLevel


def _diff_level(level: int, old_lv: MappingLevel | None,
                new_lv: MappingLevel | None, changes: list[str]) -> None:
    if old_lv is None or new_lv is None:
        changes.append(f"level {level} {'added' if new_lv is not None else 'removed'}")
        return
    if old_lv.statement != new_lv.statement:
        changes.append(f"level {level} statement: {old_lv.statement!r} → {new_lv.statement!r}")
    if old_lv.kind != new_lv.kind:
        changes.append(f"level {level} kind: {old_lv.kind!r} → {new_lv.kind!r}")
    if old_lv.context != new_lv.context:
        changes.append(f"level {level} context: {old_lv.context!r} → {new_lv.context!r}")


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
    if old.domain_pack != new.domain_pack:
        changes.append(f"domain pack changed: {old.domain_pack!r} → {new.domain_pack!r}")
    old_lv = {lv.level: lv for lv in old.levels}
    new_lv = {lv.level: lv for lv in new.levels}
    for level in sorted(set(old_lv) | set(new_lv)):
        _diff_level(level, old_lv.get(level), new_lv.get(level), changes)
    return {"mapping": new.id, "old_digest": old.digest(), "new_digest": new.digest(),
            "meaning_changed": bool(changes), "changes": changes}
