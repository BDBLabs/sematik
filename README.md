# sematik

**Semantic Conversion Engine** — governed, meaning-based data conversion.

Instead of `schema → schema`, sematik reasons across:

`Source representation → source business meaning → domain concept → temporal meaning → authority/provenance → canonical representation → transformation rule → target representation → validation → reconciliation → evidentiary record`

Migrations run through a canonical **Semantic Intermediate Representation (SIR)**:

`Legacy A → Semantic Canonical Model → Target B`

The first proving domain is California property assessment (CPASF). The
generic engine must not hard-code domain meaning — domain knowledge arrives
via versioned **Domain Packs**.

See [`docs/SPEC.md`](docs/SPEC.md) for the full requirements specification.

## Status

Pre-alpha — core semantic model, discovery/compiler/reconciliation prototypes, and tests are active. Interfaces and guarantees are still evolving.


## NVIDIA semantic embeddings

Sematik can use NVIDIA embeddings in the **Discovery plane** to rank candidate
Domain Pack concepts. Embedding similarity is evidence only: it does not approve
a mapping and is not converted into a calibrated confidence value.

Hosted NVIDIA Build:

```sh
export NVIDIA_API_KEY='nvapi-...'
```

Optional configuration:

```sh
export SEMATIK_NVIDIA_EMBEDDING_MODEL='nvidia/nemotron-3-embed-1b'
# For a self-hosted NIM:
# export SEMATIK_NVIDIA_EMBEDDINGS_URL='http://localhost:8000/v1/embeddings'
# export SEMATIK_NVIDIA_EMBEDDING_MODEL='baai/bge-m3'
```

Example:

```python
from sematik.cpasf_pack import cpasf_pack
from sematik.embeddings import NvidiaEmbeddingProvider, rank_semantic_candidates

provider = NvidiaEmbeddingProvider.from_env()
matches = rank_semantic_candidates(
    "legacy field stores assessor land value",
    cpasf_pack().canonical_concepts,
    provider,
)
for match in matches:
    print(match.concept, match.score)
```

The provider defaults to `truncate=NONE` so oversized semantic evidence fails
visibly instead of being silently truncated. See
[`ADR-0005`](docs/adr/ADR-0005-nvidia-embeddings-discovery-evidence.md).

## Development cycle (for a new model)

Sematik is GitHub-governed. `main` is gated:

1. **Read** `AGENTS.md`, `AI_ATTRIBUTION.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, and the latest ADR.
2. **Branch** from a green `main` with a name describing the unit of work
   (`ops/...`, `policy/...`, `fix/...`, `demo/...`).
3. **Implement** in the appropriate source directory; tests under `tests/`.
4. `python3 -m pytest tests -q` must be green on the branch before PR.
5. **Commit** with exact trailers (see AI_ATTRIBUTION.md §1).
6. **Push**, then **open a PR** whose body covers: what changed, why,
   requirements addressed, architectural implications, tests run, known
   limitations, and the AI Participation block.
7. **Get an independent review.** Per the owner exception, a subagent
   running a different model satisfies this; the review must cite the head
   SHA. Record the review (reviewer, Reviewed-Commit-SHA, verdict) in the PR
   as a comment and update the AI Participation fields.
8. **Do not merge without that recorded review.** Material pushes after
   approval require re-review of the new head.
9. Scratch reasoning and transient notes stay out of the repo.

The unit of work is complete when: branch deleted, PR merged by the owner,
and follow-up items captured either on GitHub issues or as PR-comment notes.
