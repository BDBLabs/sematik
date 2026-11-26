# ADR-0010: UI approval gate and Tailwind build pipeline (P0 remediation)

Date: 2026-11-26
Status: Proposed (scoped local remediation; owner acceptance required)

## Context

The UI referenced an undefined `checkApproval` handler and used Tailwind
utility class names without any CSS toolchain, so the approval button could
never work and no utility styles were compiled into the production bundle.
The Python API already owns approval policy
(`POST /api/v1/mapping/digest` → `approved`, `approval_problems`, `complete`,
`digest`; ADR-0008) and compile/run paths fail closed on unapproved mappings.

## Decision

1. `MappingEditor` implements `checkApproval` by calling the existing
   `mappingDigest` API wrapper. The UI renders authoritative status only:
   idle / checking / approved / rejected / error. Results are invalidated on
   every mapping edit, and a request sequence guard discards late responses.
2. Tailwind 3.4 is wired into the existing Vite 5 + React stack via PostCSS
   and autoprefixer, with a `src/index.css` entry imported from `main.tsx`.
3. TypeScript, React type packages, and a `typecheck` script are added;
   the invalid `DOMIterable` lib name is corrected to `DOM.Iterable`.

## Rejected alternatives

- **Client-side approval emulation** — rejected: policy and evidence binding
  live in Python; duplicating them in TS would weaken the control boundary.
- **Rewrite all utility classes as plain CSS** — rejected: large, risky
  rewrite across many components for a P0 fix; Tailwind is already implied by
  the existing class vocabulary.
- **Tailwind v4 `@tailwindcss/vite`** — rejected for this remediation: the
  repo is on Vite 5 and the PostCSS path is the smallest deterministic change.
- **`alert()` / silent handler** — rejected: no testable state or error path.

## Consequences and risks

- Approval status is local to the Mapping tab. Compile/Execute tabs remain
  enabled by the UI, but the backend fails closed; lifting an approval token
  into shared App state needs owner decision.
- The API is fail-closed without an identity provider, so live end-to-end
  approval checks require a deployment-provided provider. Verification here
  used a stubbed API through headless Chrome (no credentials or real data).
- Vite 5/esbuild development-server advisories remain (`npm audit`: 1
  moderate, 1 high); upgrading to Vite 8 is a breaking change out of scope.
- Screenshots are artifacts only; they were not visually inspected.

AI-Model: Big Pickle (big-pickle; exact upstream version unavailable)
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
