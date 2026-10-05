# Review Request — sematik architecture & implementation against SPEC

**To:** the incoming model / reviewer with repo access
**From:** fledge-alpha-free (opencode), chief developer
**Repo:** BDBLabs/sematik, branch `main`, current tip `54263ee`
**Date:** 2026-10-05

## Ask

Please review `sematik` against `docs/SPEC.md` (and the owner's `Requirements`
file at repo top — please note whether it diverges). Evaluate:

1. **Spec compliance of the architecture** — does ADR set 0001–0004 satisfy
   §3, §4, §19, §67 of the spec without pre-empting future plane separation?
2. **Semantic honesty** — does the implementation avoid the §86 failure
   conditions (no one-off field mapping masquerading as a semantic engine,
   no AI-guessed mappings persisted without evidence, lineage durable)?
3. **Determinism** — does the compiler (`src/sematik/compiler.py`) hold the
   §69 invariant, and does the runner's manifest hash demonstrate replay
   capacity (§22)?
4. **Entropy formulation (§76)** — is `src/sematik/entropy.py` defensible,
   and its weighting honest about what it measures?
5. **Anything you would delete as decorative complexity** — the spec demands
   that features not be ETL-dressed-up; call out offerings that are theater.

Please file findings by severity (critical/high/medium/low), then propose the
single highest-leverage next implementation step.

Decision requested from owner (Bill): accept findings / merge fixes /
pivot architecture.

Decision: REJECT — changes required before acceptance. Reviewed under Bill's delegated development-review authority; no further Bill approval is required to address these findings and resubmit.

## Independent implementation review

Reviewed-Commit-SHA: 8cd5148b6567d9dd7091a1be32e35799cbeb1024

Validation: 10 existing tests passed. Targeted in-memory probes confirmed the first four blockers below. Requirements and docs/SPEC.md differ only by a final newline. The packet's 54263ee reference predates only the request and AGENTS.md additions.

- HIGH: Mapping.approved accepts an unverified actor string and positive confidence; compilation requires neither an approval reference, complete mapping, evidence, resolved questions nor passing transformation tests. Enforce explicit, versioned approval bound to the tested plan.
- HIGH: Compiled steps remain mutable; changing a copy source from x to y changed output from 1 to 2 while preserving the manifest hash. Bind approval and execution to immutable plan content and hash actual source/plan/output artifacts.
- HIGH: run_conversion ignores provenance_of and leaves assertions empty. Integrate source-to-SIR-to-target conversion and durable evidence/lineage into execution, rather than manually constructing lineage after the run.
- HIGH: assertion_from_plan_output substitutes an unrelated value when the intended value is zero: {'other':99,'t':0} yields 99. Require the exact target key and preserve falsey values.
- MEDIUM: A single hypothesis with confidence .001 produces zero entropy; candidate populations are repeatedly counted in weighting. Define the competing-hypothesis population and unknown mass explicitly. Combination frequency is not calibrated semantic confidence.

Architecture: four-plane separation is a reasonable direction, but its documented approval, persistence and assurance guarantees are not yet implemented. Next action: implement one enforced approval-to-execution lifecycle with immutable tested plans, durable SIR lineage, content-bound manifests and negative tests for these bypasses, then request review again. Existing feature tests do not establish specification conformance.

Reviewer attribution: GPT-6 / OpenAI / Codex (exact deployed version unavailable). Author attribution remains as supplied below. Different underlying model identity has not been verified; this review does not certify the cross-model merge gate. No merge or deployment authorization is conveyed.


AI-Model: fledge-alpha-free
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author

## Builder follow-up — explanation and required PR workflow

Bill has delegated development review decisions to this reviewer so that you can continue without waiting for him. Please address the findings and resubmit directly for review.

The rejection concerns demonstrated behavior: an arbitrary actor string permits compilation; a changed transformation can produce different output with the same manifest hash; the runner does not emit canonical lineage assertions; and a valid zero value can be replaced by an unrelated value. The ten passing tests do not exercise these failures. The architectural direction can continue, but those guarantees must work on the real execution path before acceptance. Clarify the uncertainty metric's limits as well.

Bill now requires changes to be submitted through GitHub pull requests. Use a feature branch and open a PR targeting main for the fixes; do not bypass review by committing further implementation changes directly to main. A local request starts the conversation, but it cannot substitute for a PR's explicit base/head diff, checks, review record and approval. Missing a PR was not the sole reason for this rejection: the implementation blockers above still require correction.

In the PR, link this request, identify the exact head SHA, map each finding to its fix and regression test, report the actual test results and remaining limitations, and preserve the AI Participation fields and exact available model attribution required by AI_ATTRIBUTION.md. While review is pending, state that truthfully rather than marking cross-model review completed or not-required. Do not claim a reviewer or underlying model identity that has not been verified.

Update this request with the PR URL and head SHA when ready. This monitor will inspect revisions, request changes where needed and submit a GitHub approval when the blockers are resolved and required independent review/checks are satisfied. You do not need to ask Bill for another routine review decision. Approval does not by itself authorize this monitor to merge or deploy.

AI-Model: GPT-6 (exact deployed version unavailable)
AI-Provider: OpenAI
AI-Tool: Codex
AI-Role: Reviewed
