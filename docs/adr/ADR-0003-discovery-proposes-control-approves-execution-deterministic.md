# ADR-0003: Discovery proposes, Control approves, Execution is deterministic

Date: 2026-10-05
Status: Accepted

## Decision

- The Discovery plane may only create `SemanticHypothesis` and
  `SemanticQuestion` objects. It cannot create or modify approved mappings.
- A mapping enters the approved state only through an explicit human
  (or policy-gated machine) approval event recorded with actor, timestamp, and
  question resolution references.
- Once approved and compiled, a transformation is deterministic:
  identical source snapshot + identical versions ⇒ identical output.
  Any probabilistic inference during execution is explicit, exceptional, and
  recorded as such (spec §69).

## Rationale

Spec §38 (Explainable AI) and §39 (Model Independence) require that knowledge
live in structured form and that AI not silently promote interpretations to
production mappings. §68 requires unrecognized values to surface as explicit
exceptions rather than being coerced into defaults.

## Consequences

- Approval is a first-class event with an audit trail.
- Execution rejects inputs that do not conform to the compiled plan's shape;
  it never invents values for missing/ambiguous fields.
- The Assurance plane can diff runs across engine/mapping versions because
  every run is pinned to explicit versions.

AI-Model: fledge-alpha-free
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
