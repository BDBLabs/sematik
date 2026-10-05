# Evidence Retrieval and Semantic Investigation

Sematik is not intended to be a schema-name matcher with an LLM attached.

Its Discovery plane is intended to investigate unfamiliar systems and recover
institutional meaning from data behavior, code, documents, prior conversions,
and authorized observation of human work.

The governing principle is:

> Retrieval proposes where to investigate. Evidence supports, contradicts, or
> leaves an interpretation unresolved. Humans authorize semantic meaning.
> Deterministic code performs conversion. Assurance demonstrates what was
> preserved.

See ADR-0006 for the normative architecture contract.

## What the investigation layer does

Given a source artifact such as:

    LEGACY.PARCEL.AV_LND_01

Sematik should not immediately decide that it is assessed land value.

Instead it should create competing interpretations, for example:

- assessed land value;
- factored base-year land value;
- current market land indication;
- a historical/cache value with no current authority.

For each interpretation it should generate falsifiable predictions and gather
typed evidence.

A useful packet can include:

- column/profile behavior;
- relationships to other tables;
- source-code reads/writes;
- stored procedures and calculations;
- report labels and extracts;
- user-interface labels;
- historical value behavior;
- reconciliation against known reports/totals;
- Domain Pack definitions and aliases;
- lexical and embedding similarity;
- prior adjudicated mappings;
- authorized observations of staff using the source application;
- staff explanations, recorded separately from observed behavior.

The packet preserves contradictions. It does not average them into one magic
number.

## Evidence dimensions

Evidence has multiple dimensions because "what the software did" and "what the
information was supposed to mean" are not the same question.

### Stance

- supports;
- contradicts;
- unknown.

### Method

- executed;
- documentary;
- structural;
- similarity;
- process observation;
- human attestation.

### Authority character

- authoritative;
- operational;
- descriptive;
- inferred.

### Replay / inspection

Evidence retains a source locator and digest plus a replay record when
appropriate. A later reviewer should be able to see why a stance was proposed
and, where feasible, reproduce the probe.

## Evidence probes

A hypothesis should carry a prediction that could prove it wrong.

Example:

Hypothesis:

    BASE_VAL represents a base-year value component.

Possible predictions:

- a qualifying reassessment establishes or changes the value;
- later years factor forward from the component;
- the field participates in reports identified as base-year reporting;
- transfer/new-construction logic reads or writes it in a predictable way.

Probe families then test those predictions.

Contradiction search is symmetric: alternative interpretations receive the
same probe families wherever possible. Sematik should reveal when only the
favored interpretation has been investigated.

## Semantic precedents

Prior successful mappings are valuable, but they are precedents, not inherited
truth.

A precedent carries:

- source system and artifact;
- system/version/time scope;
- canonical concept;
- original evidence references;
- mapping digest;
- approval reference;
- known differences and exceptions.

When another legacy system contains LAND_ASSD, Sematik can retrieve relevant
precedents and explain both similarities and differences. The old mapping's
confidence or authority does not transfer automatically.

## Agent roles

The long-term Discovery plane can use multiple specialized agents.

### Source Archaeologist

Inventories schemas, files, source code, database logic, reports and metadata.
It identifies artifacts worth investigating and relationships worth testing.

### Evidence Retrieval Agent

Runs lexical, dense and hybrid retrieval over authorized institutional
knowledge. It returns passages with provenance and replay metadata, never bare
answers.

### Hypothesis and Probe Agent

Creates competing interpretations, defines falsification predictions and
requests or executes safe probes. It must actively seek contradictory evidence.

### Process Observer Agent

Runs on an authorized workstation beside a subject-matter expert and captures
structured business-process observations.

It should capture events such as:

- application/screen;
- business action;
- record/object acted upon;
- before/after state references;
- timestamp/session;
- authorized operator reference;
- evidence/screenshot/artifact locator when permitted;
- content digest and data classification.

It should not operate as an indiscriminate keylogger or credential recorder.

A useful operating mode is **Teach Mode**:

1. the agent observes an action;
2. the staff member optionally explains what they are doing and why;
3. Sematik stores the action as process-observation evidence;
4. the explanation is stored separately as human-reported evidence;
5. later probes compare the explanation with actual system behavior and
   documentary authority.

This separation is important. Staff knowledge is valuable institutional
knowledge, but observed behavior, reported understanding and governing
authority are distinct evidence types.

### Mapping Draft Agent

Builds a proposed seven-level mapping from the investigation packet. It cannot
approve it.

### Human Reviewer / SME

Adjudicates unresolved semantic questions and authorizes a mapping under the
Control-plane rules.

## Field matching is a discovery capability

Automated field matching remains an explicit product goal.

The useful version is not:

    field name -> embedding -> target field

It is:

    source artifact
      -> candidate concepts
      -> prior precedents
      -> structural/documentary/process evidence
      -> falsification probes
      -> contradiction packet
      -> human adjudication
      -> approved mapping

That process can still automate a large fraction of the labor. The system
should automate investigation and evidence assembly aggressively while keeping
semantic authority explicit.

## Evaluation

Retrieval quality must be measured before claims are made.

The initial benchmark should contain known mappings plus hard negatives such as:

- AV_LND_01 vs total assessed value;
- BASE_VAL vs base valuation date;
- BYV_FCTR vs current market value;
- owner code vs ownership percentage.

Measure recall@1, recall@5 and recall@10 for:

- lexical baseline;
- dense embeddings;
- hybrid retrieval;
- Domain Pack glossary/abbreviation expansion;
- prior-precedent retrieval.

The repository contains a small provider-neutral recall@k harness in
src/sematik/retrieval_eval.py.

## Production boundary

Retrieval and agents remain in Discovery.

Compiler, runner, golden-record execution and reconciliation cannot import
Discovery inference modules. Tests enforce that boundary.

AI-Model: GPT-5.6 Sol
AI-Provider: OpenAI
AI-Tool: ChatGPT
AI-Role: Author
