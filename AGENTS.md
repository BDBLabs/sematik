# AGENTS.md

## Project mission

Semantic Conversion Engine: meaning-based data conversion through a canonical
Semantic Intermediate Representation (SIR). Governed migrations, deterministic
execution, evidence-bound reasoning. See docs/SPEC.md and docs/ARCHITECTURE.md.

## Policy

- Read and obey [AI_ATTRIBUTION.md](AI_ATTRIBUTION.md) before creating commits
  or PRs. Every AI-authored commit must name the exact model/version and
  provider.
- Architectural decisions belong in numbered ADRs under docs/adr/.

## Ownership

- fledge-alpha-free (opencode) is chief developer.
- Another model may participate; independent review of architecture and major
  changes is requested through requests/.

## Workflow

- Python >=3.11, tests with `python3 -m pytest tests -q`.
- Every conversion runs must pass the §73 lifecycle expectations: discovery →
  hypothesis → approval → compile → execute → lineage → reconcile → manifest.
- Never let an untested transformation compile.

## Development cycle (owner directive, 2026-10-05)

GitHub is the system of record. `main` is gated.

- requirement → branch → implementation → tests → self-review → commit → push
  → pull request → independent review → owner-authorized merge.
- Do NOT commit implementation work directly to `main`.
- A unit of work gets a clearly named branch; scratch reasoning and transient
  notes stay outside the repo or in a gitignored scratch location.
- Before declaring a unit complete: review your diff, run
  `python3 -m pytest tests -q`, check `git status` for junk/secrets, commit
  with the exact AI_ATTRIBUTION.md trailers, push the branch, and open a PR
  that explains what/why/requirements addressed/architecture implications/
  tests run/known limitations/AI participation.
- The AI author must NOT merge its own PR. Stop at the review boundary; the
  independent reviewing model inspects the current head SHA. Any material
  change after approval requires re-review of the new head.
