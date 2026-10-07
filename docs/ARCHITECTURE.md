# Sematik Architecture

Status: draft v0.1 (2026-10-05)

## Planes (spec §67)

- **Discovery plane** — AI-friendly, exploratory: profiles sources, proposes
  semantic hypotheses, ranks ambiguity. Never writes to canonical mappings.
- **Semantic Control plane** — the authority for approved mappings, evidence
  graph, Domain Packs, versions, approvals. All state durable & versioned.
- **Execution plane** — deterministic, compiled transformations. No LLM calls
  at row level.
- **Assurance plane** — validation, reconciliation, invariants, manifests,
  regression (golden records), audit.

Dependencies flow downward only: Discovery → proposes to Control → Control
approves → Execution → Assurance validates. Nothing flows back *silently*;
Discoveries propose, Assurance findings become questions in Control.

## Core data model

- `Concept` — a domain concept in a Domain Pack (name, definition, aliases,
  invariants).
- `Assertion` — a claim about some fact: subject, predicate/concept, value,
  units, code-set, temporal context, derivation status, provenance, authority,
  confidence, source reference.
- `Provenance` — source system/db/table/field/record + snapshot id.
- `TemporalContext` — distinct dimensions: effective/transaction/system/event/
  recording/filing times + period; uncertainty explicit.
- `Hypothesis` — a candidate interpretation of a source artifact with
  evidence for/against, confidence, alternatives, affected records, proposed
  mapping.
- `EvidenceRef` — an artifact id + extract + stance (supports/contradicts/...).
- `Mapping` — 7 levels (physical → semantic → canonical → context → temporal →
  authority → target), confidence decomposition, rule refs.
- `Question` — first-class ambiguity object blocking conversion until
  resolved; ranked by uncertainty × impact × dependency × risk.
- `Transformation` — classification, executable plan, inputs/outputs, rule refs.
- `Run` — a conversion execution: versions, snapshot hashes, artifact hashes,
  counts, reconciliation, exceptions, approvals → `ConversionManifest`.

## Evidence Retrieval and Semantic Investigation

The Discovery plane contains an Evidence Retrieval and Semantic Investigation
layer (ERSI). It can combine structural profiling, lexical/dense retrieval,
source-code/document search, historical probes, semantic precedents and
authorized process observations.

ERSI emits typed evidence and competing interpretations to the Semantic Control
plane. It does not approve mappings.

Evidence retains stance, method, authority character, source/provenance,
replayability, scope and data classification. Sematik does not collapse
executed, documentary, structural and similarity evidence into one universal
score.

Hypotheses may carry falsification predictions. Probe families should be
symmetric across competing interpretations so the system exposes confirmation
bias rather than hiding it.

A future Process Observer Agent may capture authorized business-process events
from a legacy workstation. Observed application behavior and staff explanation
are stored as separate evidence types.

External hosted retrieval/embedding is a governed data-egress route. The
default government-oriented policy permits only PUBLIC content to external
hosted services; protected material stays local/self-hosted unless a reviewed
deployment policy explicitly permits otherwise.

Compiler, runner, golden-record execution and reconciliation are forbidden from
importing probabilistic Discovery services. Tests enforce this boundary.

See ADR-0006 and docs/SEMANTIC_INVESTIGATION.md.
## Semantic retrieval and embeddings

Embedding similarity is a **Discovery-plane signal only**. Sematik may use a
configured embedding provider to rank Domain Pack concepts against a source
description, but the resulting cosine score is not a calibrated confidence
value and cannot approve a mapping.

The first provider is NVIDIA NIM / NVIDIA Build via the OpenAI-compatible
`/v1/embeddings` contract. Provider/model/endpoint are configuration, not domain
logic. Query and passage modes remain distinct. The default policy is
fail-visible (`truncate=NONE`) rather than silently discarding source meaning.

Production Execution consumes only approved, compiled mappings; it does not call
the embedding provider for each converted row. See ADR-0005.

## Evidence graph

Nodes: source artifacts, hypotheses, assertions, concepts, mappings, rules,
transformations, runs. Edges: supports, contradicts, derives-from, maps-to,
supersedes, aliases, represents, calculated-by, populated-by, displayed-by,
reported-as, governed-by, valid-during, transformed-by, reconciled-with.

The graph is the durable, inspectable record of *why* a mapping exists.

## Domain Packs

Versioned, installable bundles: ontology/concepts, code sets, reference data,
temporal/authority rules, validation/invariant rules, known legacy patterns
(system fingerprints), conversion exemplars, reconciliation requirements,
golden records. CPASF is the first pack; the engine stays domain-agnostic.

## Compiler

Approved `Mapping` → validated SIR IR → transformation plan → executable
deterministic program (Python now; SQL later) → validation plan →
reconciliation plan. Generated artifacts must reference their source mapping,
versions, and snapshot hashes.

## Failure & determinism (spec §68/69)

- Unrecognized values, broken relationships, conflicts → explicit exception
  state. Never silent nulls/defaults.
- Approved + compiled + identical inputs/versions ⇒ identical outputs.
  Probabilistic inference during production execution is only allowed as an
  explicit, recorded exception.

## Minimum prototype (spec §73)

One messy fixture dataset → profile → hypotheses → canonical mapping →
compile → execute → trace a target record → reconcile → manifest.

AI-Model: fledge-alpha-free
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
