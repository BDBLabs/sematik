# ADR-0004: Versioning and reproducibility contract

Date: 2026-10-05
Status: Accepted

## Decision

Every conversion run records: source snapshot identity + hashes, mapping
version, Domain Pack version, engine version, transformation code version,
configuration, reference data, execution environment, and generated artifact
hashes. The Conversion Manifest is the permanent technical record (spec §58).

All versions are content-addressed where practical (e.g. sha256 of the
serialized mapping/pack/transform plan).

## Rationale

Spec §22 mandates reproducibility; §72 mandates versioning of Domain Packs,
ontology, mappings, rules, code sets, fingerprints, target profiles, tests,
and runs. AI models improve, but the product's accumulated structured
knowledge must be what grows (§39).

## Consequences

- Runs are addressable by a manifest hash; any prior run can be re-executed
  against the recorded versions.
- Semantic diffs (§60) compare versioned mapping snapshots, not repo diffs.
- Golden-record regression (§35/§61) reruns against new mapping versions.

AI-Model: fledge-alpha-free
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
