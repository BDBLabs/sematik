# ADR-0007: Shadow portable CI (Dagger + Woodpecker)

Date: 2026-10-06
Status: Proposed

## Decision

Propose a provider-independent verification baseline (Dagger module
`.dagger/src/repo_ci/`) executed in shadow mode by Woodpecker
(`.woodpecker.yml`), covering: Node workspaces when present, the Python
suite (hard-required — a pipeline that cannot run pytest fails instead of
reporting green), a production image build when a Dockerfile exists, and a
pinned Gitleaks history scan.

## Rationale

Verification must be repository-owned and runnable on any host, not tied to
one CI vendor. Shadow mode means results are informational until parity is
demonstrated.

## Consequences

- The Python gate fails closed: missing pytest with a `tests/` directory is
  an error, not a skip.
- Ruff stays advisory until the repo adopts a lint baseline.
- The Docker socket is mounted only for push/manual events, never for
  untrusted pull requests.
- Accepting this ADR (owner/chief act) is required before any cutover
  discussion; shadow results never gate merges by themselves.

AI-Model: muse-spark-1.3-contributor-free (Muse Spark 1.3 Free)
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
