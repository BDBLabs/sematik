# UI remediation — BDBLabs/sematik (P0 SEM-01 / SEM-02)

## Identity and scope

| Item | Value |
| --- | --- |
| Repository | `BDBLabs/sematik` |
| Baseline `git rev-parse HEAD` (verified clean before editing) | `8a03b5379465b616648918886eacd821e1de818e` |
| Branch | `fix/ui-remediation/sematik-p0` |
| Implementation commit SHA | `c6dd78cbf17fab4f03ca4dda167e5cfbc029d45c` |
| Evidence commit SHA | Head of this branch at review time (`git rev-parse HEAD`); a file cannot contain its own commit SHA |

Scope is limited to the Vite UI toolchain, the `MappingEditor` approval check,
and remediation evidence. Python engine/API code, governance policy, and
production configuration were not changed. No push, merge, PR, deploy,
credentials, or production data were used (per subagent assignment).

## Findings addressed

- **SEM-01 (P0)** — `ui/src/components/MappingEditor.tsx` previously called an
  undefined `checkApproval`. It now calls the repository's authoritative API
  (`POST /api/v1/mapping/digest`) through the existing `mappingDigest` helper,
  with explicit `idle | checking | approved | rejected | error` state,
  disabled/enabled button behavior, problem display, error display, stale
  result invalidation on mapping edits, and a request sequence guard.
- **SEM-02 (P0)** — Tailwind classes had no CSS pipeline. Tailwind 3.4 is now
  compiled by PostCSS + autoprefixer from `ui/src/index.css`, imported in
  `ui/src/main.tsx`; a real CSS asset is emitted by `vite build`. TypeScript,
  React type packages, a `typecheck` script, and corrected compiler
  `lib`/`types` make typechecking possible and green.

## Approach

1. Verified baseline SHA and clean worktree before any edit.
2. Captured baseline failure evidence (undefined handler, missing toolchain,
   zero CSS output) before changing files.
3. Kept approval policy on the server; the UI only renders the API result.
4. Chose the smallest Tailwind pipeline compatible with the existing Vite 5
   stack rather than rewriting component markup.
5. Ran clean install, typecheck, production build, the Python suite, and a
   headless-Chrome/CDP behavioral harness against the built app.
6. Captured desktop/mobile screenshots as artifacts; they were **not**
   visually inspected.

## Roles

- **Author / implementer:** Big Pickle (`big-pickle`, provider `opencode`),
  acting as the UI remediation subagent. Exact upstream model version was not
  exposed and is not invented.
- **Orchestrator:** the parent Big Pickle session; local commits only, no push.
- **Verification performer:** the same authoring subagent, using deterministic
  commands and a committed CDP harness. No independent cross-model review has
  been recorded on this branch.
- **Policy owner:** the Python engine/API (ADR-0008); UI does not grant approval.

## Evidence records

- [`DECISIONS.md`](DECISIONS.md) — ADR-style decisions, rejected alternatives, risks.
- [`VERIFICATION.md`](VERIFICATION.md) — exact commands/results, baseline
  failures, environment limits, residual risks.
- [`docs/adr/ADR-0010-ui-remediation-approval-gate-and-tailwind-pipeline.md`](../adr/ADR-0010-ui-remediation-approval-gate-and-tailwind-pipeline.md) —
  numbered ADR required by `AGENTS.md`.
- [`evidence/approval-cdp-harness.mjs`](evidence/approval-cdp-harness.mjs) —
  reproducible approval-gate behavior harness (stubbed API, no credentials).
- [`evidence/desktop-1440x900.png`](evidence/desktop-1440x900.png) and
  [`evidence/mobile-375x812.png`](evidence/mobile-375x812.png) — headless Chrome
  screenshot artifacts at the requested dimensions; **not visually inspected**.

## Remaining / owner decisions

- Whether to lift approval status into shared App state so the Compiler and
  Executor tabs can be disabled in the UI. Backend compile/run already fails
  closed on unapproved mappings, so this is a UI hardening choice.
- Whether to accept ADR-0010 and proceed to push/PR and independent review;
  this assignment explicitly stopped at local commits.
- Whether to upgrade Vite 5 (pre-existing dev-server advisories) in a separate
  change.
