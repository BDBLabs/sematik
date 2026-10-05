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
