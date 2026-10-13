# Issue Tracker (local working copy)

Long-lived open items. Mirror to GitHub issues as created.

- I-1 CPASF Domain Pack not yet implemented
- I-2 SIR schema needs formal versioning (spec §72)
- I-3 Discovery engine needs richer stats + FK inference
- I-4 Compiler targets only Python executor; SQL/pg unneeded for prototype
- I-5 Evidence graph persistence (currently in-memory)
- I-6 Temporal reconstruction unimplemented (spec §9/§10)
- I-7 Identity resolution unimplemented (spec §11)
- I-8 Reconciliation is population-count level; record-level + semantic (§30/§31) pending
- I-9 Human-review workflow is model-only; UI pending (§50)
- I-10 Golden Records / invariant runtime pending (§32/§35/§61)


## System-design review findings (2026-10-10)

Source: read-only architecture review of main (SPEC, ARCHITECTURE, ADR-0001..0006,
core modules, api/main.py). Test suite not run by the reviewer. Theme: governance
guarantees are implemented as checks on values supplied by the party being governed.

### High
- I-11 Approval is self-attested and does not cover the plan (§13, ADR-0003)
  - compile_mapping(mapping, steps) accepts any steps under any approved mapping.
  - golden_plan_digest is only checked non-empty; never compared to plan.digest().
  - evidence_refs are strings that resolve to nothing; blocking_question_ids is not
    linked to any SemanticQuestion and nothing in src/ sets .resolution.
  - #24 verifies fields are filled in, not that they are true.
- I-12 No durable Control plane; API trusts the client (ADR-0003, §70)
  - /execute takes mapping (incl. approved_by), steps and rows in one request body.
  - Stateless serverless, CORS "*", no auth, publicly deployed. No ApprovalEvent type
    (actor, timestamp, resolution refs). No real data may touch the live URL.
- I-13 manifest_hash is not reproducible across processes (§22, §69, ADR-0004)
  - plan.digest() hashes mapping_id (uuid4 unless supplied); manifest_hash includes it.
  - /execute builds a new Mapping per request, so identical inputs give new manifests.
  - Previously logged as "pre-existing/unrelated"; it is the §22/§69 guarantee.
  - Fix: exclude id from the digest or derive it from the digest.

### Medium
- I-14 SQL lowering still diverges from Python on derive_sum
  - Python rejects a None component; emitted SQL (a + b) returns NULL silently.
  - Numeric strings parse in Python; PostgreSQL + on text errors.
  - Add a differential test running every op both ways, including NULLs.
  - STATUS (branch fix/sql-lowering-parity-i14): derive_sum lowering now refused;
    only copy/rename lower. Executed on SQLite, 3 of 5 sample rows diverged (NULL
    component -> NULL; 'abc' + 2 -> 2, a silent wrong value; both rejected by Python).
    tests/test_sql_python_equivalence.py runs emitted SQL against the Python backend
    and fails if an op is lowered without a differential test. PostgreSQL behavior
    above is from its documented semantics, not executed here.
  - FOLLOW-UP: re-enable derive_sum only with a typed source schema (NOT NULL,
    exact/finite numeric) bound to the approval record (see ADR-0008).
- I-15 Seven mapping levels are not executable (§13, §24, §86)
  - Levels 4-6 (context, temporal, authority) are free text; nothing checks that plan
    steps implement them. Ops are only copy/rename/derive_sum/code_translate/
    assert_not_null: no predicates, temporal, identity, split/merge, unit conversion.
- I-16 Orphaned modules are not on the execution path
  - No src/ calls to IdentityRegistry, EvidenceGraph, temporal_uncertainty_flags,
    semantic_diff, rank_questions; investigation.py not used by runner or API.
  - Runner never populates TemporalContext, so every converted assertion has zero
    temporal dimensions. Mapping.evidence_refs are strings, not graph node ids.
- I-17 Entropy cannot be computed on the engine's own output (§76)
  - SemanticHypothesis has no source-artifact key; entropy groups by concept, but
    Discovery sets concept to the heuristic type, so competing meanings of one column
    never group together while the same concept across columns merges.
  - Normalizing independent confidences assumes exclusive+exhaustive; no unknown mass.
  - calibrated is a caller-set boolean (API default True), bypassing the #36 refusal.
  - /entropy/semantic-flagged returns a number anyway; remove from UI until a
    calibration set exists.
- I-18 Plane boundary is enforced on one edge only (ADR-0001)
  - Test forbids compiler/runner/golden/reconcile importing Discovery modules.
  - ADR-0001 says Assurance alone produces manifests, but manifest_hash, golden gate
    and run accounting live in runner.py (Execution). Define intended edges; test each.

### Low
- I-19 Human-review loop and small defects
  - render_request writes a Decision: line that nothing reads back (§15/§16).
  - rank_questions = records x candidate count x fan-out; candidate count is not
    uncertainty; no risk term (§16/§65).
  - Confidence defaults to calibrated=True (fail-open); Assertion defaults Confidence(1.0).
  - ConversionUngecognizable is a typo in a public exception name.
  - rename op duplicates copy.

### Scale and process
- I-20 Runner does not scale to §66 volumes
  - ConversionRun keeps all outputs and assertions in memory; manifest_hash serializes
    them whole. Needs a streaming runner and chunked/Merkle manifests.
- I-21 Tracking and review-process integrity
  - ISSUES.md is stale: I-6 (temporal) and I-7 (identity) have modules, and cpasf_pack.py
    exists against I-1. Re-scope each as "exists, not wired" or close.
  - requests/2026-10-05-review-request.md is not chronological: "Re-review 2026-10-10"
    reports 124 tests and #24 open; "Implementation update 2026-10-05" reports 144 tests
    and #24 merged.
  - gpt-6-astra appears as Reviewer (b0dee1b approval) and Author (PRs #52-#55). If the
    same model, the AGENTS.md independence gate is not met. Model identity and
    branch-protection verification (HTTP 403) remain unresolved; AI-Model trailers are
    self-attested strings.

### Recommended sequencing
1. I-11 + I-12: Control store (append-only, content-addressed) with an approval record
   binding (mapping_digest, plan_digest, golden_run_id, evidence_ids,
   resolved_question_ids, approver); compile/run take an approval id. Draft ADR-0008.
2. I-13: content-only digests (quick win, do first).
3. I-14: differential SQL/Python test across all ops.
4. I-16, I-17, I-18: wire or retire orphan modules; fix entropy grouping; test each
   plane edge.
