# ADR-0008: Control store and approval records

Date: 2026-10-10
Status: Proposed

Addresses: I-11, I-12, I-13, I-16 (see docs/ISSUES.md). Builds on ADR-0001,
ADR-0003, ADR-0004 and ADR-0006 §9. Does not supersede them.

## Context

ADR-0003 says a mapping enters the approved state "only through an explicit
approval event recorded with actor, timestamp, and question resolution
references." The code has no such event. Approval is a set of fields on
`Mapping` (`approved_by`, `approval_ref`, `evidence_refs`,
`blocking_question_ids`, `golden_plan_digest`) that `approval_problems()` checks
for presence. Review of main at c5d074f found:

- Nothing verifies those values refer to anything. `golden_plan_digest` is never
  compared to `plan.digest()`; `evidence_refs` resolve to nothing; no code sets
  `SemanticQuestion.resolution` (I-11).
- `compile_mapping(mapping, steps)` accepts any steps under any approved
  mapping, because approval covers the mapping and not the plan (I-11).
- `/api/v1/execute` receives the mapping, including `approved_by`, from the
  caller. There is no durable Control plane for the caller to be checked
  against (I-12).
- `plan.digest()` includes `mapping_id`, a `uuid4` by default, so identical
  inputs yield different manifest hashes across processes (I-13).
- Identity, evidence graph, questions, temporal and semantic-diff modules exist
  but are not connected to any execution path (I-16).

The common cause is that the party being governed supplies the evidence of its
own governance. This ADR moves authority into a store the Execution plane
cannot write to and requires approvals to reference records that exist there.

## Decision

### 1. A Control store: append-only, content-addressed events

Introduce `sematik.control`, the only module family that persists
Semantic Control state. State is a log of immutable events; current state is a
projection of that log.

Every event has:

- `id`: SHA-256 of the canonical payload (the same canonicalization used by
  `investigation._digest`; sets sorted, no timestamps, no ids generated at
  runtime);
- `kind`, `subject` (what it is about), `actor` (authenticated principal), and
  `prev` (the previous event id for the same subject, forming a per-subject
  hash chain);
- `recorded_at` and a store-assigned sequence number, kept as metadata and
  excluded from `id`.

Initial event kinds:

| Kind | Meaning |
|---|---|
| `HypothesisProposed` | Discovery output entering Control (proposal only) |
| `EvidenceAttached` | Reference to an `investigation.EvidenceItem` digest |
| `QuestionRaised` / `QuestionResolved` | Ambiguity opened / answered with decision, actor, rationale, cited evidence |
| `PlanCompiled` | (mapping_digest, plan_digest) pair |
| `GoldenRunRecorded` | (plan_digest, golden_set_digest, result) |
| `MappingApproved` | The approval record (section 2) |
| `ApprovalRevoked` | Revocation with actor and reason |
| `IdentityAssigned` / `IdentityReassigned` | Persisted `IdentityRegistry` decisions |

Storage is behind a `ControlStore` protocol. The first implementation is
SQLite (stdlib, single file, WAL mode). A Postgres implementation can follow
without changing callers.

### 2. Approval is a record that references other records

`MappingApproved` binds all of:

- `mapping_digest` and `plan_digest` (approval covers the pair, not the
  mapping alone);
- `golden_run_id` of a recorded passing run for that exact `plan_digest`;
- `evidence_ids`: `EvidenceAttached` events that exist;
- `resolved_question_ids`: `QuestionResolved` events for every question
  touching the mapping's source artifact;
- `approver` identity and `policy_id` (the governance policy applied);
- optional `signature` over the approval digest (section 6).

### 3. Verification produces an immutable token; Execution never sees the store

`control.verify_approval(store, approval_id, mapping, plan)` returns a frozen
`VerifiedApproval` (carrying the approval digest) or a list of problems. It
fails when any of the following hold:

- the approval, evidence, question or golden-run event does not exist;
- `approval.mapping_digest != mapping.digest()` or
  `approval.plan_digest != plan.digest()`;
- the golden run is for a different plan digest or did not pass;
- any question touching the artifact lacks a `QuestionResolved`;
- any `CONTRADICTS` evidence for the mapping's hypothesis is not cited by a
  resolved question (strictness is an open question, below);
- the approval has been revoked.

`compile_mapping` and `run_conversion` accept a `VerifiedApproval`, not a store
and not bare strings. `compiler.py` and `runner.py` import only the token type,
which lives in a leaf module with no store dependency. The architecture test
from ADR-0006 §9 is extended to forbid Execution modules importing the store.
This keeps the one-way flow of ADR-0001: Control approves, Execution consumes
an immutable artifact.

`Mapping.approval_problems()` is retained as `structural_problems()`: it checks
completeness (seven levels, finite confidence) and no longer claims to
establish authority.

### 4. Digests are functions of content only

No digest used in a manifest may depend on a generated id, timestamp, path, or
process state. Concretely: `Mapping.id` and `TransformationPlan.mapping_id` are
excluded from `plan.digest()`; `bound_to()` continues to check id equality at
run time. The run manifest additionally records the approval digest. Identical
source, mapping, plan, approval and engine version yield an identical manifest
hash across processes and hash seeds (ADR-0004, spec sections 22 and 69).

This section is independent of the store and ships first (phase 0).

### 5. API trust model

- `approved_by`, `approval_ref`, `golden_plan_digest` and similar fields are
  never accepted from a request body as authority.
- Production endpoints take an `approval_id` and resolve it against the store.
- The existing stateless `/execute` becomes an explicitly labeled demo mode
  that uses an in-memory store and returns `approval: demo-unverified`. It must
  not be presented as governed conversion and must not receive real data.
- Authentication is required for any endpoint that reads or writes the store.
  CORS is an explicit origin list.
- Serverless hosting without durable storage can serve only the demo mode. A
  governed deployment needs a host with a persistent volume or database.

### 6. Approver identity

Phase 1 trusts an authenticated principal supplied by the deployment (API
session, or OS user for the CLI) and records it in the event. The record shape
includes an optional ed25519 `signature` over the approval digest so that
phase 3 can require approver-held keys without a format change. Agency SSO
mapping is deployment policy, not engine logic.

### 7. Connecting the existing modules

- `questions.ingest_decision()` reads the `Decision:` line from a rendered
  request and emits `QuestionResolved` (closes the open loop in I-19).
- `IdentityRegistry` persists through `IdentityAssigned`/`IdentityReassigned`.
- `EvidenceGraph` becomes a projection of events, not a separately built
  object; `Mapping.evidence_refs` hold event ids.
- `semantic_diff` compares stored mapping versions.

## Phasing

| Phase | Scope | Closes |
|---|---|---|
| 0 | Content-only digests; cross-process manifest test | I-13 |
| 1 | `control` package, SQLite store, event kinds, `verify_approval`, `VerifiedApproval`, compile/run enforcement, boundary test | I-11 |
| 2 | API auth and `approval_id`; demo-mode labeling; question ingest | I-12, part of I-19 |
| 3 | Identity and evidence-graph projections; signed approvals; manifest records store head | I-16 |

## Alternatives considered

- **Keep string fields and add validators.** Rejected: the validator can only
  check shape; the caller still authors the content.
- **Postgres first.** Rejected for now: heavier operationally and no better
  for a single-engagement, local-first deployment. The protocol keeps the door
  open.
- **GitHub PR approval as the store.** Rejected as store: not queryable by the
  runtime and unavailable offline. It remains a valid approver-authority
  adapter.
- **Distributed ledger.** Rejected: a per-subject hash chain plus a store-head
  digest in each manifest gives tamper evidence without the machinery.

## Consequences

Positive:

- An approval cannot be forged by editing a request body, and approval of one
  plan cannot be reused for another.
- Manifests become reproducible and record which approval governed the run.
- Open questions, evidence and identity decisions become durable and
  inspectable (spec sections 6, 11, 15, 39).

Negative and risks:

- New persistence layer to operate; demo fixtures that carry `approved_by`
  strings must be migrated.
- A SQLite file can be edited by anyone with disk access. The hash chain gives
  tamper evidence, not prevention. Prevention requires OS and deployment
  controls plus anchoring the store-head digest outside the store.
- Strict contradicting-evidence rules may over-block; policy needs tuning on
  real packets.

## Acceptance tests

Negative tests, each reproducing a bypass:

- approval for plan P1 cannot compile or run plan P2;
- an approval id that does not exist, was revoked, or points to a missing
  evidence/question/golden event is rejected;
- an unresolved question, or a golden run for a different plan digest, blocks
  approval;
- `approved_by` in an API request body has no effect;
- compiler and runner modules do not import the Control store;
- manifest hash is identical across separate processes and `PYTHONHASHSEED`
  values for the same inputs.

## Open questions

1. Strictness of the contradicting-evidence rule: must every `CONTRADICTS`
   item be cited, or only unrebutted ones?
2. Who holds approver authority in an agency pilot, and how does it map to
   agency identity?
3. Classification and retention of event payloads (ties to the egress policy in
   ADR-0006 section 8).
4. Customer isolation (spec section 70): one store per engagement is the
   default assumption.
5. Whether Domain Pack version changes require their own approval events.

AI-Model: Claude Sonnet 5.5 (claude-sonnet-5-5)
AI-Provider: Anthropic
AI-Tool: Claude (claude.ai chat with desktop device bridge)
AI-Role: Drafted
