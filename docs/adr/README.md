# Architectural Design Requirements

Every major design decision gets a numbered ADR. ADRs are append-only;
supersede by adding a new one.

- ADR-0001: Four-plane separation and compiler model
- ADR-0002: SIR is the only semantic authority (schema is evidence, not authority)
- ADR-0003: Discovery proposes, Control approves, Execution is deterministic
- ADR-0004: Versioning and reproducibility contract
- ADR-0005: Embeddings are Discovery-plane evidence; NVIDIA is a pluggable provider
- ADR-0006: Evidence Retrieval and Semantic Investigation contract
- ADR-0007: Shadow portable CI (Dagger + Woodpecker) [Proposed]
- ADR-0008: Control store and approval records [Proposed]
