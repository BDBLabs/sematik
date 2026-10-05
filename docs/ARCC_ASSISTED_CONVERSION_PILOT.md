# ARCC-Assisted Data Conversion Pilot Readiness

## Position

Sematik is **not production-ready today to autonomously convert ARCC data**.

It can, however, be developed into a credible assisted-discovery and conversion
pilot tool for ARCC much sooner than it can become a fully autonomous migration
engine.

The near-term value proposition is to reduce the labor and uncertainty in:

- source-system inventory;
- field/concept discovery;
- institutional-knowledge recovery;
- mapping proposal;
- ambiguity identification;
- evidence assembly;
- historical validation;
- controlled sample conversion;
- reconciliation planning.

Human SMEs remain responsible for semantic adjudication and conversion
authorization.

## Why ARCC is a strong proving environment

A mature assessor environment contains exactly the conditions Sematik is meant
to handle:

- legacy field names and abbreviations;
- business meaning distributed across code, reports, data dictionaries and
  institutional memory;
- temporal concepts that cannot be flattened;
- legally consequential distinctions;
- multiple source and downstream systems;
- long operational history;
- high value in proving what information meant before it is transformed.

The CPASF Domain Pack provides a canonical vocabulary and domain constraints
without hard-coding ARCC meaning into the generic engine.

## Proposed pilot

### Phase 0 — Governance and data boundary

Before source data is ingested:

- classify source artifacts;
- decide what can remain local, what can be self-hosted, and what may use an
  external hosted provider;
- establish authorized users and workstation-observation consent;
- identify restricted/PII data and redaction rules;
- freeze a source snapshot for the pilot.

Exit criterion: approved access/egress plan and reproducible pilot snapshot.

### Phase 1 — Source archaeology

Inventory a bounded source area such as one valuation or transfer workflow.

Collect authorized examples of:

- tables/columns;
- database relationships;
- stored procedures;
- source code;
- report definitions;
- screen labels;
- data dictionaries;
- conversion notes;
- procedures/SOPs;
- relevant Domain Pack concepts.

Exit criterion: source-artifact catalog with provenance.

### Phase 2 — Known-answer benchmark

Select fields whose meaning is already well understood by ARCC SMEs.

Use them to measure:

- lexical retrieval;
- dense retrieval;
- hybrid retrieval;
- abbreviation/glossary expansion;
- semantic-precedent retrieval.

Track recall@1, recall@5 and recall@10. Include hard negatives.

Exit criterion: measured retrieval baseline, not anecdotal quality claims.

### Phase 3 — Semantic investigation

For less-understood fields:

1. create competing interpretations;
2. attach falsification predictions;
3. retrieve documentary and similarity evidence;
4. inspect structural relationships;
5. run historical behavior/reconciliation probes;
6. search symmetrically for contradiction;
7. surface unresolved questions.

Exit criterion: reviewable investigation packet for each selected concept.

### Phase 4 — Process-knowledge capture

Run an authorized observer beside an appraiser or other SME performing a
selected legacy workflow.

Use two channels:

- **observed process:** what the application/user actually did;
- **reported explanation:** what the SME says the action means and why.

Do not merge those channels.

A useful Teach Mode session can capture:

- screen/application;
- record/object;
- action;
- before/after artifact references;
- relevant field names;
- user explanation;
- temporal/business context;
- source/evidence digest.

Exit criterion: process observations incorporated into investigation packets
without credential/raw-keylogging capture.

### Phase 5 — Human semantic adjudication

ARCC SMEs review competing interpretations and evidence.

Approved mappings must remain bound to:

- evidence;
- scope;
- source snapshot/system version;
- mapping version;
- approval;
- unresolved-question disposition.

Exit criterion: approved pilot mapping set.

### Phase 6 — Deterministic sample conversion

Compile approved mappings and convert a controlled sample.

No retrieval, LLM or embedding call occurs in this execution path.

Exit criterion: deterministic replay under identical versions and input.

### Phase 7 — Assurance

Perform:

- record-level reconciliation;
- population reconciliation;
- temporal checks;
- domain invariants;
- golden-record regression;
- semantic loss reporting;
- trace from target record back to source and approval evidence.

Exit criterion: documented discrepancies and a replayable conversion manifest.

## What an ARCC pilot should prove

The pilot is successful if Sematik can answer for selected source artifacts:

- What are the plausible meanings?
- What evidence supports each interpretation?
- What evidence contradicts each interpretation?
- What does historical behavior show?
- What did staff understand the process to mean?
- What authority applies?
- What remains unresolved?
- Which mapping did a human approve?
- Can the approved transformation be replayed deterministically?
- Did the target preserve the materially important meaning?

## What it should not claim yet

Until production gates are satisfied, Sematik should not claim:

- autonomous semantic authority;
- production-safe unattended conversion;
- comprehensive ARCC system understanding;
- legal correctness derived from historical software behavior;
- that embedding similarity is mapping confidence;
- that a successful aggregate balance proves semantic correctness.

## Pilot recommendation

The best first ARCC proving slice is a workflow with:

- known SMEs;
- enough legacy complexity to test semantic discovery;
- a bounded set of source artifacts;
- historical examples for deterministic validation;
- a clear CPASF target representation.

A transfer/change-of-ownership or a bounded valuation-component workflow may be
strong candidates because both include field semantics, temporal behavior,
reports, business rules and staff process knowledge.

Final pilot scope should be selected with ARCC based on data availability and
operational risk.

AI-Model: GPT-5.6 Sol
AI-Provider: OpenAI
AI-Tool: ChatGPT
AI-Role: Author
