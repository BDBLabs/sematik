# ADR-0006: Evidence Retrieval and Semantic Investigation contract

**Status:** Accepted  
**Date:** 2026-10-05  
**Accepted:** 2026-10-11, at the repository owner's instruction (Bill Parris, in chat). Acceptance records the decision, not completion: the "Pilot posture" section still governs what may be claimed, and sections 8 and 10 are implemented incrementally (see PR #60 for section 8; the section 10 evaluation harness is in progress).

## Context

Sematik is intended to help recover the meaning of unfamiliar enterprise
systems, not merely match column names. Dense embeddings, lexical retrieval,
source profiling, code search, historical behavior, documentation, and observed
human workflows can all reduce the search space during discovery.

None of those sources is semantic authority by itself.

The system therefore needs a contract between the exploratory Discovery plane
and the governed Semantic Control plane. The contract must preserve conflicting
evidence, make investigation falsifiable, prevent probabilistic tools from
entering deterministic execution, and control data egress when hosted services
are used.

Issues #38 and #39 identify the immediate implementation gaps. PR #34 provides
an embedding primitive, but not the investigation system described here.

## Decision

### 1. Create an Evidence Retrieval and Semantic Investigation layer

Evidence Retrieval and Semantic Investigation (ERSI) is part of the Discovery
plane. It may:

- profile source data and behavior;
- retrieve lexical and semantic matches;
- search source code, reports, procedures, tickets, documentation and other
  authorized institutional knowledge;
- compare prior adjudicated mappings;
- generate competing interpretations;
- define falsifiable predictions;
- run or request evidence probes;
- collect authorized process observations from source applications;
- assemble a review packet for the Semantic Control plane.

ERSI may not approve a mapping.

### 2. Evidence remains typed and multidimensional

Sematik will not collapse heterogeneous evidence into one universal score.

Every evidence item records at least:

- stance: supports, contradicts, or unknown;
- method: executed, documentary, structural, similarity, process observation,
  or human attestation;
- authority character: authoritative, operational, descriptive, or inferred;
- source locator/span and full content digest;
- producer and replay record;
- scope;
- data classification.

Observed behavior and governing meaning are different dimensions. A legacy
program can consistently perform behavior that is not authoritative.

Similarity is evidence of resemblance only. It is never approval and is not a
calibrated Sematik Confidence value.

### 3. Hypotheses must be falsifiable

A serious semantic interpretation should carry one or more falsification
predictions: observable behavior that would differ if the interpretation were
wrong.

Evidence probes are explicit objects bound to a prediction and a hypothesis.

Examples include:

- historical reconciliation;
- value-distribution behavior;
- event/temporal behavior;
- source-code branch analysis;
- report/document lookup;
- relationship testing;
- lexical/dense retrieval.

Executed evidence is generally the strongest evidence of what a system actually
did. It is not automatically the strongest evidence of what the data was
legally or operationally supposed to mean.

### 4. Contradiction search is symmetric

Retrieval must not only seek material that confirms the favored interpretation.

For each competing interpretation, Sematik should support equivalent probe
families and adversarial/negation searches. Investigation packets expose
incomplete symmetric coverage rather than hiding it.

### 5. LLM-assigned stance is a proposal

An LLM may propose that a source span supports or contradicts a hypothesis, but
that judgment must be recorded with:

- the exact source span or locator;
- source digest;
- model/tool producer;
- replay parameters/result digest;
- inferred authority;
- reviewability.

The LLM judgment does not transform the underlying source into higher-authority
evidence.

### 6. Prior mappings become Semantic Precedents

A reusable prior mapping retains:

- source artifact;
- canonical concept;
- original mapping digest;
- approval reference;
- evidence references;
- source-system/version/temporal scope;
- known local differences.

A precedent may inform a new investigation. Its confidence and authority never
transfer automatically to another system.

### 7. Process-knowledge capture is an explicit Discovery capability

Sematik may eventually run an authorized observer agent beside a subject-matter
expert using a legacy application.

The observer records business-process events such as:

- application/screen or source artifact;
- business action performed;
- object/record acted upon;
- timestamp/session/authorized actor reference;
- resulting system state or evidence locator;
- content digest and data classification;
- optional operator explanation.

The observer must not silently keylog passwords, capture unrestricted screen
content, or treat observed behavior as authoritative meaning. Raw observations
enter investigation as unknown-stance operational evidence until interpreted.

This capability is intended to recover institutional knowledge that may exist
only in practice and staff experience.

### 8. Data egress is fail-closed

External hosted retrieval/embedding is an explicit egress route.

The baseline government-oriented policy is:

- PUBLIC: may be allowed to reviewed external hosted providers;
- INTERNAL/CONFIDENTIAL/RESTRICTED: local or self-hosted inside the customer-controlled trust boundary by default;
- deployment owners may substitute a stricter or specifically approved policy.

Possession of an API key is not permission to send customer data.

Credentials may be sent only over HTTPS or cleartext loopback for local
development. Every egress operation should be bound to purpose,
classification, destination, and content digest.

### 9. Execution plane cannot depend on retrieval/investigation

Compiler, runner, golden-record execution, and reconciliation must not import
embedding, retrieval, investigation, agent, or hosted-inference modules.

This is an executable architecture invariant, not only documentation.

Approved deterministic artifacts cross the Control -> Execution boundary.
Probabilistic Discovery services do not.

### 10. Retrieval quality must be measured

No claim such as "dramatically reduces search space" is considered established
without an evaluation set.

The initial evaluation should include known domain mappings, abbreviations and
hard negatives and report at minimum:

- recall@1;
- recall@5;
- recall@10;
- lexical-only baseline;
- dense-only baseline;
- hybrid baseline;
- Domain Pack glossary/abbreviation expansion effects;
- abstention behavior.

## Consequences

Sematik becomes more than a field matcher while retaining a strict human and
evidence authority model.

The near-term product can assist a conversion team with discovery, semantic
mapping proposals, evidence packets, process knowledge capture, and
reconciliation design before it is trusted to autonomously execute production
migration decisions.

The evidence model intentionally contains more structure than a conventional
RAG response. That structure is necessary for traceability, contradiction,
replay and later audit.

## Pilot posture

This ADR does not claim Sematik is production-ready for agency data conversion.

A credible agency-assisted pilot can begin when Sematik can demonstrate a vertical
slice over authorized sample material:

1. ingest an agency-like source schema and mixed institutional artifacts;
2. generate competing field/concept interpretations;
3. retrieve documentary, structural and similarity evidence;
4. run at least one deterministic historical/reconciliation probe;
5. surface contradiction and unresolved questions;
6. capture an authorized process observation and attach it to the packet;
7. obtain human adjudication;
8. compile an approved deterministic mapping;
9. convert a controlled sample;
10. reconcile and produce replayable evidence.

Production use requires the remaining execution, assurance, security and
deployment gates to pass independently.

## References

- ADR-0001: four-plane separation
- ADR-0002: SIR is semantic authority
- ADR-0003: Discovery proposes; Control approves; Execution is deterministic
- ADR-0004: versioning and reproducibility
- Issue #38: institutional-knowledge retrieval gap
- Issue #39: data-egress policy
- PR #34: NVIDIA embedding primitive

AI-Model: GPT-5.6 Sol
AI-Provider: OpenAI
AI-Tool: ChatGPT
AI-Role: Author
