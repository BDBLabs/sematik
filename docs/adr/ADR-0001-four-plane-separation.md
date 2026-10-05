# ADR-0001: Four-plane separation and compiler model

Date: 2026-10-05
Status: Accepted

## Decision

Separate the engine into four planes with one-way information flow:

- **Discovery** — profiling, hypotheses, ambiguity ranking. Mutates nothing
  canonical; only *proposes*.
- **Semantic Control** — approved Domain Packs, mappings, evidence graph,
  questions, versions, approvals. Durable and versioned.
- **Execution** — deterministic compiled transformations over compiled
  mappings. No probabilistic inference at row level.
- **Assurance** — validation, reconciliation, invariants, manifests, golden
  records, regression.

A Mapping must compile before it can execute: Mapping → SIR-IR → transformation
plan → executable transform → validation plan → reconciliation plan.

## Rationale

Spec §67 requires this separation; §66 requires production execution to be
deterministic and scalable; §86 forbids production AI guesses per row.
Discovery is exploratory and mutating would dissolve the audit boundary;
execution without a compiled mapping would make runs unreproducible.

## Consequences

- Discovery output (hypotheses) and approved control-plane state are distinct
  object types with distinct types and storage.
- The Execution plane owns no domain policy; it only runs compiled plans.
- The Assurance plane is the only producer of manifests and the only consumer
  of both sides of a conversion run.

AI-Model: fledge-alpha-free
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
