# Verification record — sematik UI remediation

Baseline SHA: `8a03b5379465b616648918886eacd821e1de818e` (verified clean before edits).
Branch: `fix/ui-remediation/sematik-p0`.
Implementation commit: `c6dd78cbf17fab4f03ca4dda167e5cfbc029d45c`.
Environment: macOS, Node `v22.23.4`, npm `12.2.0`, Python `3.13.17`,
Vite `5.4.21`, Google Chrome at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.

## Status summary

| Verification | Status | Exact evidence |
| --- | --- | --- |
| Baseline HEAD + clean tree | **passed** | `git rev-parse HEAD` → `8a03b5379465b616648918886eacd821e1de818e`; `git status --short` empty |
| Baseline typecheck (repo script) | **failed (baseline)** | `npx tsc --noEmit` → `This is not the tsc command you are looking for`, `TSC_EXIT=1` |
| Baseline typecheck (one-off compiler) | **failed (baseline)** | `npx -y -p typescript@5.6.3 tsc --noEmit` → 541 `error TS` lines, exit 2; includes `src/components/MappingEditor.tsx(186,18): error TS2304: Cannot find name 'checkApproval'.` |
| Baseline CSS pipeline | **failed (baseline)** | `npm run build` exit 0, but `find dist -type f` → `dist/assets/index-C_yB_yUR.js`, `dist/index.html`; **no CSS asset** and no stylesheet link |
| Final clean install | **passed** | `rm -rf node_modules && npm ci` → `added 135 packages...`, `NPM_CI_EXIT=0` |
| Final typecheck | **passed** | `npm run typecheck` → only npm notices, `TYPECHECK_EXIT=0` |
| Final production build | **passed** | `npm run build` → `✓ 41 modules transformed`, `dist/assets/index-CJiBSS9I.css 11.92 kB`, `dist/assets/index-CZh4vPyc.js 175.41 kB`, `BUILD_EXIT=0` |
| Compiled utility classes | **passed** | `grep` on built CSS found `.bg-slate-900`, `.space-y-4`, `.grid-cols-2`, `.text-green-400`, `.disabled\:opacity-50` |
| Python suite | **passed** | `python3 -m pytest tests -q` → `234 passed, 1 warning in 7.80s`, `PYTEST_EXIT=0` |
| Approval-gate behavior (CDP) | **passed** | `node docs/ui-remediation/evidence/approval-cdp-harness.mjs` → `SUMMARY total=20 passed=20 failed=0`, `CDP_EXIT=0` |
| Desktop screenshot artifact | **passed (artifact only)** | Chrome wrote `47260 bytes` to `docs/ui-remediation/evidence/desktop-1440x900.png`; `file` → `PNG image data, 1440 x 900`. Chrome exit 2 from teardown watchdog (see Environment limits) |
| Mobile screenshot artifact | **passed (artifact only)** | Chrome wrote `34610 bytes` to `docs/ui-remediation/evidence/mobile-375x812.png`; `file` → `PNG image data, 375 x 812`; `MOBILE_EXIT=0` |
| Visual inspection of screenshots | **not-run** | No screenshot was visually inspected by this agent; no visual claim is made |
| Live API approval end-to-end | **blocked** | `POST /api/v1/mapping/digest` via TestClient → `status= 503 body= {"detail":"authentication unavailable"}`; deployment must provide an identity provider |
| Push / PR / independent review | **not-run** | Assignment forbids push, merge, PR, deploy; no cross-model review recorded |
| CI wiring for `typecheck` | **not-run** | Script exists locally; CI change out of scoped assignment |

## Baseline failure evidence (captured before any edit)

`npm ci` on the untouched tree:

```text
added 63 packages, and audited 64 packages in 4s
2 vulnerabilities (1 moderate, 1 high)
npm warn install-scripts 2 packages had install scripts blocked because they are not covered by allowScripts:
npm warn install-scripts   esbuild@0.21.5 (postinstall: node install.js)
```

`npx tsc --noEmit` (repository had no TypeScript dependency):

```text
This is not the tsc command you are looking for
TSC_EXIT=1
```

`npx -y -p typescript@5.6.3 tsc --noEmit` (relevant lines from 541 errors):

```text
src/components/MappingEditor.tsx(42,16): error TS2345: Argument of type '{ source_artifact?: string | undefined; canonical_concept?: string | undefined; ... }' is not assignable to parameter of type 'MappingIn'.
src/components/MappingEditor.tsx(186,18): error TS2304: Cannot find name 'checkApproval'.
tsconfig.json(5,20): error TS6046: Argument for '--lib' option must be: ... 'dom.iterable', ...
```

`npm run build` on the untouched tree:

```text
vite v5.4.21 building for production...
✓ 40 modules transformed.
dist/index.html                  0.63 kB │ gzip:  0.45 kB
dist/assets/index-C_yB_yUR.js  173.14 kB │ gzip: 52.41 kB
✓ built in 1.35s
BUILD_EXIT=0

--- dist contents ---
dist/assets/index-C_yB_yUR.js
dist/index.html
```

This is the SEM-02 failure mode: the build reports success while every
Tailwind utility class in `ui/src` remains an uninterpreted JSX string.

## Final commands and results

Run from `ui/`:

```text
rm -rf node_modules && npm ci        -> exit 0 (135 packages; 2 dev advisories)
npm run typecheck                    -> exit 0 (no diagnostics)
rm -rf dist && npm run build         -> exit 0 (CSS + JS emitted)
python3 -m pytest tests -q           -> 234 passed, 1 warning in 7.80s (exit 0)
npm audit --omit=dev                 -> found 0 vulnerabilities
npm audit                            -> 2 vulnerabilities (1 moderate esbuild, 1 high vite); both are pre-existing dev-server advisories
git diff --check                     -> no whitespace errors
```

Built CSS utility check (from `dist/assets/index-CJiBSS9I.css`):
`bg-slate-900`, `space-y-4`, `grid-cols-2`, `text-green-400`,
`disabled\:opacity-50`, `hover\:bg-blue-700`, `bg-slate-800\/50` — all present.

## Approval-gate harness (behavioral verification)

Setup (local only):

```text
cd ui && npm run preview -- --port 4173 --strictPort
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --headless=new --disable-gpu --no-first-run --hide-scrollbars --remote-debugging-port=9222 --user-data-dir=<temp-profile> about:blank
node docs/ui-remediation/evidence/approval-cdp-harness.mjs
```

The harness stubs `fetch` in the page with in-memory fixtures; it uses no
credentials and no production data. Exact result lines:

```text
PASS app mounted: nav element present
PASS open Mapping tab: clicked Mapping tab
PASS check button disabled with no mapping: {"label":"Check approval status","disabled":true,"busy":null}
PASS load demo mapping: clicked load demo
PASS check button enabled with mapping: {"label":"Check approval status","disabled":false,"busy":"false"}
PASS approved scenario click: clicked check
PASS approved status rendered: Approved — digest aaaaaaaaaaaa…
PASS edit mapping field: dispatched input event on source artifact
PASS edit resets approval state: {"label":"Check approval status","disabled":false,"busy":"false"}
PASS rejected scenario click: clicked check
PASS rejected status rendered: Not approved — resolve the problems below before compiling or executing.
PASS approval problems listed: ["• no approver recorded","• semantic levels missing: [1]"]
PASS error scenario click: clicked re-check
PASS API failure handled in UI: API 500: boom
PASS slow scenario click: clicked re-check
PASS button disabled while checking: {"label":"Checking approval…","disabled":true,"busy":"true"}
PASS slow check completes: Approved — digest aaaaaaaaaaaa…
PASS stale scenario click: clicked re-check (slow)
PASS stale: checking started: {"label":"Checking approval…","disabled":true,"busy":"true"}
PASS stale result discarded after edit: {"label":"Check approval status","disabled":false,"busy":"false"} approvedText=false
SUMMARY total=20 passed=20 failed=0
```

## Screenshot commands (exact)

```text
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --headless=new --disable-gpu --no-first-run --hide-scrollbars --window-size=1440,900 --virtual-time-budget=6000 --screenshot=docs/ui-remediation/evidence/desktop-1440x900.png http://localhost:4173
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --headless=new --disable-gpu --no-first-run --hide-scrollbars --window-size=375,812 --virtual-time-budget=6000 --screenshot=docs/ui-remediation/evidence/mobile-375x812.png http://localhost:4173
```

Results: `47260 bytes written` for desktop (Chrome exit 2: `Teardown watchdog
expired; recording dump and terminating`, plus non-fatal `CVDisplayLinkCreate...
failed` / `Trying to load the allocator multiple times` warnings); `34610 bytes
written` for mobile (exit 0 on rerun). `file` and `sips -g pixelWidth -g
pixelHeight` confirmed `1440 x 900` and `375 x 812` PNGs. SHA-256:
`cf40c82c3c3063308ffe37800947b98e61c451e4e4b3990ff6ba24f94d536ae1`
(desktop), `ef88c51c5ee6d040e39513b53fbac21d3660008905fa192d4b2304e0d1a41567`
(mobile). These are artifacts only — not visually inspected.

## Environment limits and failures

- `npm ci` reports install scripts blocked for `esbuild` and `fsevents` by the
  local npm allow-scripts policy. Builds still succeeded; no approval was
  granted by this agent.
- Chrome teardown warnings/exit 2 on the desktop capture did not prevent a
  complete, correctly sized PNG; mobile exited 0 on rerun.
- The API has no production identity provider (`api/auth.py` returns `None`),
  so live protected routes return 503. Therefore screenshots show the app's
  offline path and the approval gate was verified with a stubbed API.
- No screenshot was reviewed by a human or a vision-capable model here; layout
  quality is unverified.

## Lessons and residual risks

- A green `vite build` is not a typecheck; SEM-01 survived because no
  TypeScript compiler or `typecheck` script existed. Typecheck is now a
  required local gate.
- A green build is not a CSS pipeline; SEM-02 survived because class strings
  were emitted verbatim in JS. CSS artifact presence and utility presence are
  now checked explicitly.
- Approval status is not lifted into shared App state; Compiler/Executor
  buttons can still be clicked, though the backend fails closed. Owner choice
  recorded in `README.md` / `DECISIONS.md`.
- Vite 5/esbuild dev-server advisories remain (pre-existing at baseline);
  `npm audit --omit=dev` is clean. Upgrading Vite is a breaking change and was
  not performed.
- CI does not yet run `npm run typecheck`; this branch stops at local commits.

AI-Model: Big Pickle (big-pickle; exact upstream version unavailable)
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
