# ADR-0009: Institutional understanding foundation

Status: Proposed

Source: owner's foundational product vision, recorded in
[PRODUCT_VISION.md](../PRODUCT_VISION.md).

## Context and authority

Sematik's product mission now explicitly encompasses institutional understanding
throughout an organization's life. Conversion remains a major application.
This proposal reconciles that direction with the repository at `1f97bd3`.
It records architectural proposals, not a claim of completed platform capability.
No existing ADR is superseded or promoted to Accepted by this document.

The specification already supplies substantial foundations: SIR (§4), evidence
(§6–8), time and history (§9–10), expert review (§15–16), authority (§28), durable
model-independent knowledge (§39), semantic memory (§42), legacy retirement and
knowledge preservation (§53–55), and institutional knowledge recovery (§82).
The gap is making their lifecycle independent of a migration target or run.

## Reconciliation with existing decisions

| Contract | Disposition under the broader mission |
|---|---|
| ADR-0001, Accepted: four planes | Retain. Discovery investigates; Control governs semantic state; Execution consumes approved artifacts; Assurance checks evidence and outcomes. Non-conversion inquiry need not execute a transformation. |
| ADR-0002, Accepted: SIR semantic authority | Retain canonical structured meaning. Propose extending SIR concepts to processes, decisions, relationships and rules without requiring a target mapping. SIR stores authority claims; it does not create legal or organizational authority. |
| ADR-0003, Accepted: explicit approval and deterministic execution | Retain. Evidence collection and SME statements do not automatically authorize conclusions. Application-specific approval remains required for consequential use. |
| ADR-0004, Accepted: versions and reproducibility | Retain conversion manifests; propose versioned understanding snapshots and dependency references for other consumers. Do not relabel an inquiry as a conversion run. |
| ADR-0005 and ADR-0006, Proposed: embeddings and investigation | Reuse existing primitives and proposed boundaries; similarity remains evidence only. Their Proposed status remains unchanged. |
| ADR-0007, Proposed: portable CI | Unchanged; broader product scope does not authorize CI cutover. |
| ADR-0008, Proposed: Control store | Build on the proposal, but verify enforcement before relying on it. Current partial implementation does not establish accepted architecture or production governance. |
| SPEC §1–2, §50, §89–90 | Interpret as conversion application scope under the owner's product mission. Preserve numbered requirements and conversion acceptance tests. |
| SPEC §42–46: reuse and cross-customer learning | Same-client reuse remains permission-bound. Cross-client reuse requires explicit rights, authorization and review, including derived patterns, embeddings and precedents. Removing names is not sufficient authorization. |

## Current components and proposed reuse

This inventory is based on source inspection, not a production readiness audit.

| Component and evidence | Current state / coupling | Proposed platform role and gap |
|---|---|---|
| `model.py`: Assertion, Provenance, TemporalContext, DerivationStatus | Structured semantic primitives exist; provenance emphasizes database locations. | Reuse as SIR foundation; extend source locators and governed links for documents, people, processes and decisions. Preserve observed, reported, inferred and authorized distinctions. |
| `evidence.py`: EvidenceGraph | In-memory nodes/edges with JSON import/export; supports and contradicts relationships. | Durable institutional evidence service with referential integrity, version history, access enforcement and permission-aware traversal. JSON serialization alone is not managed durable storage. |
| `investigation.py`: InvestigationPacket, EvidenceItem, probes | Competing interpretations, source spans/digests, stance and symmetric probe coverage exist. | Reuse for institutional questions without target mappings. Automating ingestion, retrieval and probes remains separate integration work. |
| `embeddings.py`, `handbook.py`, `retrieval_eval.py`, `egress.py` | Retrieval, evaluation and egress primitives exist. | Authorized source discovery and evidence retrieval; retrieval results do not constitute understanding. Add consistent permission filtering across indexes, caches and outputs. |
| `domain_pack.py`, `cpasf_pack.py` | CPASF supplies concepts, code sets, invariants and known patterns. DomainPack also defines corpus and golden-record fields, empty by default. | Keep shared domain definitions versioned; separate optional conversion profiles through compatible interfaces when needed. Client overlays and rights must remain explicit. |
| `temporal.py`, `identity.py`, `semantic_diff.py` | Temporal coverage/uncertainty helpers, identity and mapping comparison primitives; temporal module explicitly defers full reconstruction. | Governed historical views, durable identity and change impact. Do not claim historical reconstruction from coverage counters. |
| `questions.py`, ProcessObservation in `investigation.py` | Questions render review requests; process-observation type exists. Teach Mode is described in SEMANTIC_INVESTIGATION.md. | Expert-learning workflow retaining observations and explanations separately. A deployed observer, adjudication lifecycle and complete Teach Mode are not established by these primitives. |
| `control.py`, `compiler.py`, `api/main.py` | SQLite event store and verifier exist; compiler approval token is optional, API still accepts approval fields from callers. | Candidate governance foundation, with mandatory authenticated and scoped approvals, revocation and reference validation still requiring work. Do not expose client knowledge on the strength of type definitions alone. |
| `mapping.py`, `compiler.py`, `runner.py`, `golden.py`, `reconcile.py` | Seven-level mappings, target plans, conversion execution and assurance are application-specific. | Preserve the conversion engine as a consumer of approved understanding. Reuse assurance concepts through explicit contracts; retain conversion lifecycle and deterministic execution checks. |

## Proposed service boundaries

These are logical contracts within the current repository; they do not require
microservices, a new graph database, a code move or a rewrite.

1. **Knowledge capture:** preserve authorized source artifacts and revisions with
   ownership, classification, source digest, locator, recorded time, retention and
   permitted purpose. Capture material from people and institutional systems.
2. **Investigation:** link artifacts to competing interpretations and falsification
   probes. Record support, contradiction, unknowns, methods and producers. An
   investigation can end unresolved without a target field or conversion run.
3. **Semantic Control:** manage versioned concepts, assertions, relationships,
   questions, authority scope and adjudication. A proposed understanding record
   references supporting and contradicting evidence, temporal applicability,
   provenance, review status, unresolved questions and supersession history.
4. **Understanding access:** answer authorized questions and expose structured
   explanations with evidence and uncertainty. Consumers pin the versions they
   used. Unsupported interpretations must remain proposals or abstentions.
5. **Application consumption and assurance:** conversion, institutional inquiry,
   staff onboarding and change-impact analysis consume the same permitted
   knowledge. Each application applies its own authorization and acceptance
   criteria; approval for one purpose does not automatically authorize another.

Discovery can submit new proposals after assurance findings; it cannot silently
rewrite approved understanding. Changed or revoked evidence triggers dependency
review and a new version, preserving the historical explanation and applicable
retention rules. Current conclusions and historical authorized states remain
distinguishable.

## Governance requirements for reuse

Tenant and actor identity must come from trusted authentication, with checks on
ingest, retrieval, graph traversal, inference inputs, approval and export. Scope
must propagate to derived artifacts, summaries, embeddings, caches, traces and
logs. A separate engagement store can assist isolation but does not replace
authorization. Source ownership and restrictions remain attached to derivatives.

Reuse is scoped to tenant, purpose, authority, system/version and time. Missing
authorization denies access. Even public classification does not by itself grant
cross-client redistribution rights. Generic Domain Packs require independent
provenance and licensing; client knowledge cannot silently enter shared packs.
Retention, lawful deletion and withdrawal must cover derivatives and indexes,
with audit records retained only as permitted by policy.

## Incremental delivery and acceptance

1. Record the owner mission and review this reconciliation. Resolve Proposed ADRs
   through existing governance; do not rewrite accepted ADRs.
2. Establish durable, authenticated, tenant-scoped Control and evidence storage;
   close the approval bypasses before treating either as platform infrastructure.
3. Demonstrate one institutional question without a migration target: collect a
   policy, historical system evidence and an expert explanation; preserve a
   contradiction; record scoped adjudication and remaining uncertainty. Restart
   the service and reproduce the same versioned explanation with source locators.
4. Reuse that understanding in both an authorized institutional explanation and
   a conversion mapping. Prove neither requires rediscovery, and that conversion
   still passes compile, golden-record, lineage, reconciliation and manifest gates.
5. Exercise policy changes, evidence withdrawal and historic/current queries.
   Verify dependent consumers are flagged without silently changing prior outputs.

Required evidence includes denied cross-tenant access through direct IDs,
retrieval, graph traversal, caches and exports; classification and source
restrictions preserved or strengthened on derivatives, with any downgrade
requiring explicit authorization; revoked approval rejection; preserved contradiction; and separation
of observation, expert explanation, inference and authorized conclusion.
Evaluate explanation traceability, historical correctness, uncertainty disclosure,
expert effort and reuse across applications alongside retrieval quality. Do not
invent a universal numeric “understanding” score.

## Consequences and remaining decisions

The mission broadens while the working conversion investment remains useful.
Delivery adds governance and durable evidence work before broader client use;
renaming the product does not satisfy those requirements.

Review must decide the versioned understanding schema, authority and adjudicator
roles, retention/withdrawal rules, and the first non-conversion pilot. Implementation
PRs should identify the reusable capability, consumer-specific behavior, source
rights, evidence/temporal requirements and acceptance evidence.

AI-Model: gpt-6-astra
AI-Provider: OpenAI
AI-Tool: Codex
AI-Role: Drafted
