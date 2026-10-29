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

## PR review exception (owner directive, 2026-10-05)

An independent reviewer is still preferred, but as an explicit exception the
authoring agent may obtain PR review from subagents. Where the subagent runs a
different underlying model from the author, its review satisfies the
independent-review requirement. Where no different model is available, the
exception requires a per-PR note from the owner in chat. The author does not
merge a PR until the required review is recorded.

## Archive branch isolation (mandatory)

Recovered `archive/*` branches and closed historical pull requests are **evidence**, not active assignments. They must never become a coding agent's default task source, branch base, merge queue item, deployment target, or CI execution target.

- Start new work only from the current authorized default branch (normally `main`) or an explicitly assigned, approved feature branch. Ignore `archive/*` refs when selecting tasks, enumerating active work, suggesting merges, cleaning up branches, or generating release notes.
- Do not reopen or create PRs from archive refs; do not checkout, build, test, run, cherry-pick, rebase, delete, force-push, or rewrite archived code without a task-specific human authorization and independent current-state review. Reading historical diffs and evidence is permitted for research, subject to access controls.
- Never treat a restored branch or a closed PR as current authority; cite the original PR, its disposition, and exact head SHA when consulting it. Reimplementation should be created afresh from current `main`, with its own PR and verification.
- Keep `archive/**` excluded from privileged CI, deployment and branch automation. If an existing workflow matches archived refs, report it rather than running untrusted historical code; changes to GitHub workflow rules require review.
- For archival, retention, legal hold, rights, and evidence manifest requirements, read [DEVELOPMENT_EVIDENCE_RETENTION.md](DEVELOPMENT_EVIDENCE_RETENTION.md). Preserve original provenance and human authority. Do not commit raw session transcripts, credentials, or sensitive external records.

These rules become active in this repository only when the containing policy PR is independently reviewed and merged; meanwhile the owner has directed custodians to avoid reusing the restored archives.
