# UI remediation decisions — sematik (2026-11-26)

These are ADR-style records for the scoped P0 remediation. The governing
numbered ADR is
[ADR-0010](../adr/ADR-0010-ui-remediation-approval-gate-and-tailwind-pipeline.md)
(Status: Proposed; owner acceptance required). Baseline:
`8a03b5379465b616648918886eacd821e1de818e`; branch:
`fix/ui-remediation/sematik-p0`; implementation commit:
`c6dd78cbf17fab4f03ca4dda167e5cfbc029d45c`.

## D1 — Approval is checked by the API, not by the browser

**Decision.** `checkApproval` calls `POST /api/v1/mapping/digest` through the
existing `mappingDigest` wrapper. UI state is
`idle | checking | approved | rejected | error`; the button is disabled while
checking and when no mapping exists; edits reset the result; a request counter
discards late responses.

**Rationale.** `src/sematik/mapping.py` defines approval problems (approver,
reference, version, confidence, seven levels, evidence, golden plan) and
`src/sematik/compiler.py` / `runner.py` fail closed. Duplicating those rules in
TypeScript would create a second, weaker policy source and contradict ADR-0008.

**Rejected alternatives.**

- Local client-side approval calculation: rejected (policy duplication, drift).
- `window.alert()` on error: rejected (untestable, no durable state).
- Stubbed/no-op handler to silence the compiler: rejected (would fake a gate).

**Risks.** The approval status is local to the Mapping tab, so a user can still
click Compile/Execute; the server rejects unapproved work. The API is
fail-closed without a deployment identity provider, so live checks cannot be
exercised in this environment.

## D2 — Tailwind 3.4 via PostCSS in the existing Vite 5 stack

**Decision.** Add `tailwindcss`, `postcss`, and `autoprefixer` dev
dependencies, `tailwind.config.js`, `postcss.config.js`, and
`ui/src/index.css` with `@tailwind base/components/utilities`, imported from
`main.tsx`. Content scanning covers `index.html` and `src/**/*.{ts,tsx}`.

**Rationale.** The code already uses Tailwind vocabulary; Vite handles PostCSS
natively. This produces a real CSS artifact (`dist/assets/*.css`) and keeps the
change small.

**Rejected alternatives.**

- Rewrite all utility classes as hand-written CSS: rejected (large blast
  radius across every component, risk of visual regressions we cannot inspect).
- Tailwind v4 `@tailwindcss/vite`: rejected for this P0 (repo is on Vite 5;
  more migration surface than needed).
- Leave inline `<style>` as the only CSS: rejected (utilities never compile —
  the confirmed SEM-02 failure).

**Risks.** Utility generation depends on content globs; new files outside the
globs would need config updates. `@tailwind base` preflight changes some
default element styling; the prior inline base rules were moved into
`@layer base` to preserve body font/background/color.

## D3 — Make typechecking a first-class, passing check

**Decision.** Add `typescript` + `@types/react` + `@types/react-dom` dev
dependencies and a `typecheck` npm script; fix `DOMIterable` → `DOM.Iterable`
and add `vite/client` types; give `updateMapping` explicit required defaults.

**Rationale.** SEM-01's undefined handler was invisible to the build because
Vite transpiles without typechecking. A green `tsc --noEmit` now catches this
class of defect.

**Rejected alternatives.**

- Rely on `vite build` alone: rejected (it passed on the broken baseline).
- Suppress the errors with `any` / `// @ts-ignore`: rejected (weakens checks).

**Risks.** Typecheck is a local script, not yet wired into CI; CI wiring is an
owner decision.

## D4 — Verification without production access

**Decision.** Use a committed CDP harness with a stubbed, in-memory API to
exercise approval states; run the Python suite and real builds locally; capture
screenshots as artifacts only.

**Rationale.** `api/auth.py` intentionally fails closed with no identity
provider and forbids environment flags for test credentials. Never use real
credentials or production data.

**Rejected alternatives.**

- Add a dev auth bypass: rejected (weakens a security boundary).
- Claim screenshot-based visual confirmation: rejected (screenshots were not
  visually inspected).

**Risks.** Stubbed verification proves UI wiring and state transitions, not
live provider authorization; screenshots are unread artifacts here.

AI-Model: Big Pickle (big-pickle; exact upstream version unavailable)
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
