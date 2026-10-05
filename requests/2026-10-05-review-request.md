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

Decision:

AI-Model: fledge-alpha-free
AI-Provider: opencode
AI-Tool: OpenCode
AI-Role: Author
