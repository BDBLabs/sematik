# ADR-0005: Embeddings are Discovery-plane evidence; NVIDIA is a pluggable provider

**Status:** Proposed  
**Date:** 2026-10-05

## Context

Sematik needs semantic retrieval that can recognize equivalent business meaning
when source and canonical names differ. Dense embeddings are useful for proposing
candidate concepts, but they are probabilistic and model-dependent.

The architecture already requires Discovery to propose and the Semantic Control
plane to approve. Embedding similarity must not bypass that boundary.

NVIDIA currently exposes an OpenAI-compatible embeddings API at
`/v1/embeddings`. Hosted NVIDIA Build requests use
`https://integrate.api.nvidia.com/v1/embeddings` and `NVIDIA_API_KEY`.
Sematik also needs to support self-hosted NVIDIA NIMs for private and
air-gapped deployments.

## Decision

1. Add a provider-neutral `EmbeddingProvider` protocol in
   `sematik.embeddings`.
2. Implement `NvidiaEmbeddingProvider` with the hosted NVIDIA endpoint as the
   default and with endpoint/model overrides for self-hosted NIM.
3. Default the hosted model to `nvidia/nemotron-3-embed-1b`, the current NVIDIA hosted text-embedding model, while allowing the model to be changed without changing Sematik code.
4. Preserve NVIDIA's retrieval semantics:
   - source descriptions are embedded as `query`;
   - canonical concept definitions are embedded as `passage`.
5. Default to `truncate=NONE`. Overlong semantic evidence must fail visibly
   rather than being silently truncated.
6. Return cosine similarity as `SemanticSimilarity.score`. It is evidence,
   not calibrated `Confidence`, not an approved Mapping, and not authority.
7. Record provider, model and a digest of the source description on each
   candidate result.
8. Keep embedding calls in the Discovery plane. Compiled production conversion
   remains deterministic and does not call an embedding model row-by-row.

## Configuration

Hosted NVIDIA Build:

```text
NVIDIA_API_KEY=nvapi-...
SEMATIK_NVIDIA_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b
```

Optional endpoint override for self-hosted NIM:

```text
SEMATIK_NVIDIA_EMBEDDINGS_URL=http://embedding-nim:8000/v1/embeddings
SEMATIK_NVIDIA_EMBEDDING_MODEL=baai/bge-m3
```

A self-hosted endpoint may omit `NVIDIA_API_KEY` if the deployment itself does
not require authentication.

## Consequences

- Semantic candidate generation improves without making embeddings semantic
  authority.
- NVIDIA hosted inference can be adopted now while preserving a path to
  private/self-hosted NIM.
- BGE-M3 remains usable as a configured model, but Sematik is not coupled to it.
- Changing embedding models invalidates direct vector comparability; caches and
  persisted similarity evidence must therefore be model-version scoped.
- A hosted model ID alone may not prove immutable model weights. High-assurance
  reproducibility should use a revision-pinned/self-hosted model or retain
  provider/model-version evidence when the service exposes it.
- API keys remain runtime secrets and must never be committed.

## Non-goals

This ADR does not authorize automatic mappings from embedding scores, does not
define a vector database, and does not move probabilistic inference into the
Execution plane.

AI-Model: GPT-5.6 Sol
AI-Provider: OpenAI
AI-Tool: ChatGPT
AI-Role: Author
