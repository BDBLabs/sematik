"""Embedding providers and semantic candidate ranking for the Discovery plane.

Embeddings are evidence, not semantic authority. Similarity can propose
candidate concepts, but it cannot approve a Mapping or become a calibrated
Confidence value without independent evidence (ADR-0003 / spec section 67).
"""

from __future__ import annotations

import hashlib
import json
import ipaddress
import math
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Literal, Protocol, Sequence

InputType = Literal["query", "passage"]

DEFAULT_NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/embeddings"
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3-embed-1b"


class EmbeddingError(RuntimeError):
    """Base error for embedding-provider failures."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when an embedding provider is configured unsafely or incompletely."""


class EmbeddingResponseError(EmbeddingError):
    """Raised when a provider returns a malformed or unusable embedding response."""


class EmbeddingProvider(Protocol):
    """Minimal provider contract used by the semantic discovery plane."""

    provider_name: str
    model: str

    def embed(self, texts: Sequence[str], *, input_type: InputType) -> list[list[float]]:
        """Return one dense vector per input text in the same order."""


@dataclass(frozen=True)
class SemanticSimilarity:
    """One embedding-derived candidate.

    score is cosine similarity, not calibrated confidence and not approval.
    """

    concept: str
    definition: str
    score: float
    provider: str
    model: str
    source_digest: str



def _credential_transport_allowed(endpoint: str) -> bool:
    parsed = urlparse(endpoint)
    if not parsed.hostname:
        return False
    if parsed.scheme == "https":
        return True
    if parsed.scheme != "http":
        return False
    if parsed.hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


@dataclass
class NvidiaEmbeddingProvider:
    """NVIDIA NIM / NVIDIA Build embedding client.

    The hosted default is NVIDIA's OpenAI-compatible embeddings endpoint.
    A self-hosted NIM can be used by passing another endpoint; authentication
    is optional for self-hosted deployments and mandatory for NVIDIA's hosted
    endpoint.
    """

    endpoint: str = DEFAULT_NVIDIA_ENDPOINT
    model: str = DEFAULT_NVIDIA_MODEL
    api_key: str | None = None
    timeout_seconds: float = 30.0
    truncate: Literal["START", "END", "NONE"] = "NONE"
    dimensions: int | None = None
    provider_name: str = "nvidia"

    def __post_init__(self) -> None:
        if not self.endpoint.startswith(("https://", "http://")):
            raise EmbeddingConfigurationError("embedding endpoint must be http(s)")
        if not self.model.strip():
            raise EmbeddingConfigurationError("embedding model is required")
        if self.truncate not in {"START", "END", "NONE"}:
            raise EmbeddingConfigurationError("truncate must be START, END, or NONE")
        if self.dimensions is not None and self.dimensions <= 0:
            raise EmbeddingConfigurationError("dimensions must be positive")
        if self.endpoint.startswith("https://integrate.api.nvidia.com/") and not self.api_key:
            raise EmbeddingConfigurationError(
                "NVIDIA_API_KEY is required for the hosted NVIDIA embeddings endpoint"
            )
        if self.api_key and not _credential_transport_allowed(self.endpoint):
            raise EmbeddingConfigurationError(
                "API credentials require HTTPS or a cleartext loopback endpoint"
            )

    @classmethod
    def from_env(cls) -> "NvidiaEmbeddingProvider":
        """Construct from Sematik/NVIDIA environment variables."""

        endpoint = os.getenv("SEMATIK_NVIDIA_EMBEDDINGS_URL", DEFAULT_NVIDIA_ENDPOINT)
        model = os.getenv("SEMATIK_NVIDIA_EMBEDDING_MODEL", DEFAULT_NVIDIA_MODEL)
        api_key = os.getenv("NVIDIA_API_KEY") or None
        raw_dimensions = os.getenv("SEMATIK_NVIDIA_EMBEDDING_DIMENSIONS", "").strip()
        try:
            dimensions = int(raw_dimensions) if raw_dimensions else None
        except ValueError as exc:
            raise EmbeddingConfigurationError(
                "SEMATIK_NVIDIA_EMBEDDING_DIMENSIONS must be an integer"
            ) from exc
        return cls(
            endpoint=endpoint,
            model=model,
            api_key=api_key,
            dimensions=dimensions,
        )

    def embed(self, texts: Sequence[str], *, input_type: InputType) -> list[list[float]]:
        if input_type not in {"query", "passage"}:
            raise ValueError("input_type must be 'query' or 'passage'")
        values = list(texts)
        if not values:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in values):
            raise ValueError("embedding inputs must be non-empty strings")

        payload: dict[str, object] = {
            "input": values,
            "model": self.model,
            "input_type": input_type,
            "encoding_format": "float",
            "truncate": self.truncate,
        }
        if self.dimensions is not None:
            payload["dimensions"] = self.dimensions

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "sematik-nvidia-embeddings/0.1",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            # Do not echo provider response bodies: they can reflect source text.
            raise EmbeddingError(f"NVIDIA embeddings HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise EmbeddingError(f"NVIDIA embeddings request failed: {exc.reason}") from exc

        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise EmbeddingResponseError("NVIDIA embeddings response was not valid JSON") from exc

        if not isinstance(body, dict):
            raise EmbeddingResponseError("NVIDIA embeddings response must be a JSON object")
        response_model = body.get("model")
        if response_model is not None and response_model != self.model:
            raise EmbeddingResponseError(
                f"embedding response model {response_model!r} does not match requested {self.model!r}"
            )

        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(values):
            raise EmbeddingResponseError(
                f"expected {len(values)} embeddings, received "
                f"{len(data) if isinstance(data, list) else 'invalid data'}"
            )

        indexed: dict[int, list[float]] = {}
        vector_size: int | None = None
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("index"), int):
                raise EmbeddingResponseError("embedding item is missing an integer index")
            index = item["index"]
            raw_vector = item.get("embedding")
            if not isinstance(raw_vector, list) or not raw_vector:
                raise EmbeddingResponseError(f"embedding {index} is missing a vector")
            vector: list[float] = []
            for value in raw_vector:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise EmbeddingResponseError(f"embedding {index} contains a non-numeric value")
                number = float(value)
                if not math.isfinite(number):
                    raise EmbeddingResponseError(f"embedding {index} contains a non-finite value")
                vector.append(number)
            if vector_size is None:
                vector_size = len(vector)
            elif len(vector) != vector_size:
                raise EmbeddingResponseError("embedding vectors have inconsistent dimensions")
            if index in indexed:
                raise EmbeddingResponseError(f"duplicate embedding index {index}")
            indexed[index] = vector

        expected_indices = set(range(len(values)))
        if set(indexed) != expected_indices:
            raise EmbeddingResponseError(
                f"embedding indices {sorted(indexed)} do not match expected "
                f"{sorted(expected_indices)}"
            )
        return [indexed[i] for i in range(len(values))]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity for float embeddings."""

    if len(left) != len(right) or not left:
        raise ValueError("embedding vectors must be non-empty and have equal dimensions")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("cannot compare a zero embedding vector")
    return dot / (left_norm * right_norm)


def rank_semantic_candidates(
    source_description: str,
    concepts: dict[str, str],
    provider: EmbeddingProvider,
    *,
    top_k: int = 5,
) -> list[SemanticSimilarity]:
    """Rank canonical concepts as Discovery-plane candidates.

    The source description is embedded as a query and canonical concept
    definitions as passage inputs. Scores are deliberately returned as raw
    semantic-similarity evidence; callers must not treat them as approval or as
    calibrated Confidence values.
    """

    if not source_description.strip():
        raise ValueError("source_description is required")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if not concepts:
        return []

    concept_items = list(concepts.items())
    query_vectors = provider.embed([source_description], input_type="query")
    if len(query_vectors) != 1:
        raise EmbeddingResponseError("provider returned the wrong number of query embeddings")
    query = query_vectors[0]
    passage_texts = [f"{concept}: {definition}" for concept, definition in concept_items]
    passages = provider.embed(passage_texts, input_type="passage")
    if len(passages) != len(concept_items):
        raise EmbeddingResponseError("provider returned the wrong number of passage embeddings")

    source_digest = hashlib.sha256(source_description.encode("utf-8")).hexdigest()
    ranked = [
        SemanticSimilarity(
            concept=concept,
            definition=definition,
            score=cosine_similarity(query, vector),
            provider=provider.provider_name,
            model=provider.model,
            source_digest=source_digest,
        )
        for (concept, definition), vector in zip(concept_items, passages)
    ]
    ranked.sort(key=lambda match: (-match.score, match.concept))
    return ranked[: min(top_k, len(ranked))]
