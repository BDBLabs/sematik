# ADR-0002: SIR is the only semantic authority

Date: 2026-10-05
Status: Accepted

## Decision

All migration reasoning is recorded against the Semantic Intermediate
Representation (SIR) — machine-readable assertions, concepts, mappings,
hypotheses, evidence, temporal context, confidence.

Physical source schemas, field names, and target schemas are *evidence*, never
authority (spec §8). A target representation is a *compiled projection* of the
canonical model, not the semantic source of truth.

## Rationale

Spec §3 requires a canonical intermediate representation so that
`Legacy A → CPASF → Vendor X` and later `Legacy A → CPASF → Vendor Y` do not
re-discover Legacy A. If physical schemas became authority, every new target
would require a new custom transformation and the platform would degrade into
ETL (spec §86 failure condition #1).

## Consequences

- `Assertion` carries provenance, derivation status, temporal context,
  confidence, and transformation history — all durable.
- Confidence is decomposable (drivers, not just a percentage) — §14.
- DerivationStatus (observed/reported/derived/estimate/inference/authorized/
  reference/system-artifact) is preserved across conversion.

AI-Model: fledge-alpha-free
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
