# ADR-0009: Teach Mode and a shared institutional knowledge foundation

**Status:** Accepted product and architectural direction (owner-endorsed); implementation pending

**Date:** 2026-10-14

**Decision owner:** William Parris

**Decision source:** Owner's voice discussion and explicit request to record this direction in the repository.

Acceptance records the intended direction, not implemented functionality,
production readiness, or approval of a particular deployment. The pilot sequence
and unresolved design choices below are recommendations, not additional owner
decisions. Sematik remains the working name; no replacement name was selected.

## Context and relationship to existing decisions

Sematik should preserve the knowledge needed to understand an organization's
work while converting the data that supports it. That knowledge includes
business meanings, procedures, rationale, exceptions, historical context,
supporting evidence, and relationships between legacy and successor systems.
Institutional memory is a core product outcome that continues after migration.

This makes concrete the knowledge-preservation objectives in
[SPEC sections 53–55](../SPEC.md#53-migration-digital-twin), together with
section 39 (model independence), section 47 (natural-language query), and
section 71 (API-first architecture). It extends the Teach Mode direction in
[Semantic Investigation](../SEMANTIC_INVESTIGATION.md) and the
[assisted conversion pilot](../ASSISTED_CONVERSION_PILOT.md).

It builds on [ADR-0006](ADR-0006-evidence-retrieval-semantic-investigation.md)
for typed evidence and Discovery boundaries and aligns with the proposed
[ADR-0008](ADR-0008-control-store-and-approval-records.md) approval-record
contract. It does not supersede prior ADRs, change their recorded status, or
declare their proposed capabilities complete. The four-plane separation and
canonical semantic authority remain intact.

### Current implementation baseline

At repository revision `a4c4fb7`, inspected for this record:

- `ui/src/App.tsx` exposes eight engine-operation tabs. This is a rudimentary
  console for exercising API operations, not the final guided user product.
- The Profiler calls `ui/src/api.ts`, which calls `api/main.py`; the profile and
  hypothesis endpoints invoke `src/sematik/discovery.py`. That path uses basic
  statistical heuristics for suggestions such as identifiers, flags, and sparse
  columns. It does not demonstrate end-to-end intelligent source-to-target
  matching or the apprenticeship described here.
- The documents already describe investigation and knowledge preservation.
  Their presence is not implementation evidence for a complete Teach Mode
  agent, durable knowledge portal, or autonomous enterprise understanding.

The owner's initial concern about the UI's appearance was revised after
recognizing its API-console role. Preserve that useful separation while
designing a guided product experience. This ADR authorizes neither a UI
implementation nor a product rename.

## Decision

### 1. One learning process produces two durable assets

Sematik will use one evidence-based learning process to produce:

1. **Conversion knowledge:** business meaning precise enough to propose, test,
   review, approve, and execute source-to-target mappings.
2. **An institutional knowledge portal:** a gateway people can consult, correct,
   and improve after the old system is replaced.

These are connected views of the same governed knowledge foundation. The
portal is not an incidental export of migration documentation, and conversion
mappings must not become an isolated knowledge silo.

### 2. Teach Mode is an interactive apprenticeship

At a new client, an agent learns alongside staff during authorized work.
Employees know when it is observing and choose when and where it observes,
within organizational authorization. They can pause or end the observation.
They are active teachers, contributors, and reviewers.

The interaction should:

1. Observe a selected business action and its permitted context.
2. Ask useful questions, such as why a value changed, when it would differ,
   which exceptions apply, or who can explain an unfamiliar step.
3. Keep the observed action separate from the employee's explanation.
4. Summarize the agent's understanding for employee correction.
5. Persist the resulting claims, evidence, corrections, and open questions
   with their review state.

Questions should be timed or batched around natural pauses so work is not
constantly interrupted. Staff can defer questions and demonstrate alternatives.
Observation does not imply permission to operate the business application.
There must be no indiscriminate keylogging or credential capture.

Apply the existing classification, access, retention, and deployment/egress
policies to recordings, screenshots, transcripts, summaries, and derived
records. Participation in Teach Mode does not grant blanket cloud permission.

### 3. Learn both the legacy and successor environments

The owner suggested roughly a month of initial legacy learning, followed by
similar learning of the target through vendor demonstrations, sandbox work,
training classes, and staff workflows. This is an illustrative discovery
timebox, not a fixed schedule or a guarantee of completeness. Source and target
learning may overlap as access permits.

A coverage/gap register must track workflows, variants, periods, exceptions,
available evidence, review status, and missing demonstrations. Rare, annual,
exceptional, and historical processes require targeted investigation; absence
from the observed month does not mean they do not exist.

Vendor demonstrations and training are evidence of described behavior. Test
target behavior in an authorized environment and bind results to the relevant
configuration and version before relying on that behavior for conversion.

### 4. Ground business actions in data and evidence

Screens alone cannot establish physical database mappings. Connect authorized
observations and staff explanations to schema metadata, sample data,
documentation, application logs or code where available, and controlled probes.
When that connection cannot be established, retain an explicit gap.

Keep the following distinguishable:

| Record | What it establishes |
| --- | --- |
| Observed behavior | What was seen or executed in a particular context |
| Human-reported understanding | What a staff member says an action or value means |
| Documentary/policy authority | What an identified source prescribes within its scope |
| Machine inference | A proposed interpretation or relationship requiring evaluation |
| Approved decision | What an authorized reviewer decided for a defined scope/version |

Each claim must retain provenance and evidence locators, scope, relevant time
and system/version, producer, and review state. Preserve supporting and
contradicting evidence. Local workarounds may conflict with authoritative rules;
neither repeated behavior nor a persuasive explanation silently resolves that
conflict. Corrections must retain the history needed to understand what changed.

### 5. Shared concepts connect source meaning to target representations

Discovery learns source business meaning and target representations through
shared semantic concepts, rather than relying on superficial field-name
matching. A proposed mapping carries its evidence, alternative interpretations,
unresolved questions, and validation/test cases.

The existing separation remains mandatory:

- **Discovery** proposes hypotheses, investigations, mappings, and questions.
- **Semantic Control** provides human/authorized review and approval tied to
  the applicable evidence, scope, versions, and transformation plan.
- **Execution** consumes approved, compiled transformations deterministically;
  there are no row-level LLM calls in this path.
- **Assurance** tests and reconciles results. Findings return as explicit
  questions, not silent changes to approved meaning.

Staff explanations, model summaries, similarity scores, and portal answers do
not become approved truth automatically. Review of a process explanation is
not authorization to execute a conversion.

### 6. Persistent knowledge outlives both the model session and legacy system

Persistent memory belongs in a structured, versioned knowledge/evidence store,
not a month-long model context or an undifferentiated transcript archive.
Summaries need links to retained evidence, and the system must expose evidence
that is unavailable or restricted rather than invent support for a claim.

The knowledge foundation should connect processes, business concepts, source
and target artifacts, explanations, evidence, questions, decisions, mappings,
and validation results. Corrections and later system changes must remain
traceable under ongoing stewardship and retention/access policy.

A future portal question might be: "How do I perform this correction in the
successor system, why does the process exist, and how was the relevant legacy
data carried over?" Its answer should connect the reviewed procedure, rationale,
historical meaning, applicable mapping, and supporting evidence. It must show
scope and unresolved uncertainty rather than presenting every stored claim as
equally authoritative. Knowledge remains correctable after legacy retirement.

### 7. Preserve UI, API, and core-engine separation

The guided UI, knowledge portal, and authorized integrations should use the
API. Authority, access checks, validation, and approval enforcement remain in
the backend; a client cannot establish authority merely by displaying an
approved state or supplying an approver name.

API separation supports multiple clients and keeps presentation separate from
the core engine. It is not, by itself, a security guarantee. Existing backend,
identity, persistence, and deployment gaps require their own implementation and
verification. This record does not select a new visual design.

## Feasibility and limits

Available components support a supervised pilot and integration effort:

- Microsoft documents desktop task recording and analysis in its
  [task mining overview](https://learn.microsoft.com/en-us/power-automate/task-mining-overview).
- OpenAI documents audio/text interaction, image inputs, and function calling
  in [Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations).
- OpenAI documents screenshot-based interaction loops in
  [computer use](https://developers.openai.com/api/docs/guides/tools-computer-use).

These sources were checked on 2026-10-14. They establish component capabilities,
not Sematik implementation, procurement choices, permission to send client data,
or reliable autonomous understanding of an enterprise. Retrieval and structured
persistence are integration building blocks; their existence does not prove the
quality or completeness of the knowledge collected.

The main engineering work is grounding business actions in data/evidence,
asking useful questions, incorporating review and corrections, tracking
uncertainty and coverage, and persisting knowledge reliably within authorization.
The direction is feasible to test under supervision. No claim of uniqueness,
complete understanding, or unattended production readiness follows from it.

## Recommended first proof and staged pilot

Start with **one employee teaching one bounded workflow**. Produce both a
reviewed process explanation and an evidence-backed proposed mapping with
executable validation/test cases. Demonstrate both outputs against the same
evidence, including an exception or contradiction where present.

Suggested stages, subject to pilot scope and implementation decisions:

1. Agree on the workflow, access/observation boundary, retained evidence, staff
   reviewer, and known gaps.
2. Observe, ask, summarize, and correct; persist the process explanation and
   its evidence/review state.
3. Ground the explanation in source artifacts and shared concepts; investigate
   the target using authorized training, sandbox work, and probes.
4. Produce a proposed mapping, alternatives, unresolved questions, and
   executable cases with reviewed expectations; run permitted validation.
5. Demonstrate portal retrieval of the reviewed process and its relationship
   to the proposed mapping, with traceable citations and visible uncertainty.
6. Only after approval and execution gates are implemented and satisfied,
   compile and run a controlled sample and reconcile it under the existing
   assisted-pilot requirements.

Evaluate demonstrated coverage, accuracy, staff corrections, unresolved gaps,
evidence traceability, and test results before expanding. This ADR invents no
quantitative acceptance threshold. Passing the bounded proof does not establish
enterprise-wide coverage or production readiness.

## Consequences and open implementation decisions

The product must support continuing knowledge stewardship alongside migration
delivery. This increases the persistence, review, access-control, evidence,
versioning, and user-experience work. It also makes the learning investment
useful after cutover and exposes gaps that a simple field-matching UI would hide.

Decisions still needed include the first workflow/client boundary; authorized
capture mechanisms; question timing and deferral; employee correction workflow;
knowledge-store schema and retrieval interfaces; alignment with the proposed
Control store; portal stewardship and stale-knowledge handling; target-system
access; and pilot acceptance measures. Model/provider and deployment choices
remain subject to policy. Product naming and UI implementation remain separate
work.

Alternatives not selected are treating institutional knowledge as a disposable
migration report, keeping portal knowledge separate from mapping evidence,
using passive screen recording without staff correction, or relying on model
context as durable memory. Each loses either the connected evidence, human
review, or lasting institutional value required by this direction.

AI-Assisted: yes

AI-Model: GPT-6 (family exposed; exact variant/version unavailable)

AI-Provider: OpenAI

AI-Tool: Codex desktop

AI-Role: Drafted
