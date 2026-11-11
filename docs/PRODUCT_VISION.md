# Sematik: foundational product vision

Status: owner-directed product scope; architecture implementation remains subject
to repository review and accepted ADRs.

This directive takes precedence over any narrower description of Sematik as
solely a data conversion or migration engine.

Sematik exists to become the institutional knowledge and understanding foundation
for its clients. Its purpose is to capture, preserve, organize, connect,
investigate, and interpret institutional knowledge so that an organization can
understand its own systems, operations, rules, history, decisions, and
relationships.

Sematik must distinguish between possessing information and understanding its
meaning. It must transform fragmented institutional knowledge into a durable,
evidence-supported model of how an institution operates.

## Core principles

1. **Knowledge is the foundation.** Sematik must preserve knowledge from people,
   documents, applications, databases, processes, policies, and historical records.
2. **Understanding is the product.** Retrieval alone is insufficient. Sematik must
   establish relationships, reconstruct context, identify contradictions, explain
   interpretations, and preserve uncertainty.
3. **Institutional memory must survive change.** Knowledge should remain usable
   when employees retire, software is replaced, vendors change, or historical
   context is lost.
4. **Evidence must accompany understanding.** Every consequential interpretation
   should be traceable to its supporting and contradicting evidence, provenance,
   temporal scope, and applicable authority.
5. **Human expertise remains essential.** Sematik should learn through interaction
   with institutional experts while distinguishing observed behavior, human
   explanations, inferred meaning, and formally authorized conclusions.
6. **Understanding must be reusable.** Once Sematik establishes institutional
   knowledge, that understanding should support multiple authorized applications
   without requiring the institution to rediscover its meaning for every new project.
7. **Data conversion is a major application, not the product boundary.** The
   Semantic Conversion Engine, SIR, Domain Packs, Evidence Graph, and Teach Mode
   should contribute to the larger institutional understanding architecture.
8. **Client knowledge requires governance.** Preserve tenant isolation, access
   controls, source ownership, confidentiality, data classification, and
   authorization. Never assume one client's knowledge can be reused for another
   client.

## Orchestrator responsibility

Evaluate all existing and proposed architecture against this broader mission.
Identify which current components form the foundation of an institutional
understanding platform and which are narrowly coupled to conversion.

Do not discard the conversion engine or rewrite working code merely to reflect
the expanded vision. Determine how its semantic modeling, evidence, retrieval,
temporal reasoning, and governance capabilities can become reusable platform
services.

Treat this as a product-level architectural clarification requiring reconciliation
with existing specifications and accepted ADRs, not as permission to silently
override repository governance.

The ultimate goal is not simply to move an institution's data. It is to preserve
and develop the institution's understanding of itself, then make that understanding
useful.

## Relationship to the repository

- [SPEC.md](SPEC.md) retains its numbered conversion requirements and acceptance
  criteria. Its conversion-only product framing is qualified by this directive.
- [ARCHITECTURE.md](ARCHITECTURE.md) describes the current design.
- [ADR-0009](adr/ADR-0009-institutional-understanding-foundation.md) is the proposed
  architectural reconciliation. Product direction is owner-supplied; proposed
  service contracts and implementation sequencing still require review.
- Accepted ADRs are append-only. Any necessary supersession requires a new ADR
  and the repository's approval process. Existing Proposed ADRs remain Proposed.

Source: owner directive supplied in chat, “SEMATIK: FOUNDATIONAL PRODUCT VISION.”
Core principles and orchestrator direction retained from that directive; repository
cross-references added by the drafting agent.

AI-Model: gpt-6-astra
AI-Provider: OpenAI
AI-Tool: Codex
AI-Role: Drafted
