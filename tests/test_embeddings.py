import json

import pytest

from sematik.embeddings import (
    DEFAULT_NVIDIA_ENDPOINT,
    EmbeddingConfigurationError,
    EmbeddingResponseError,
    NvidiaEmbeddingProvider,
    rank_semantic_candidates,
)


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def test_nvidia_provider_sends_query_mode_and_preserves_response_order(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["authorization"] = request.get_header("Authorization")
        seen["payload"] = json.loads(request.data)
        return _Response({
            "object": "list",
            "model": "nvidia/llama-nemotron-embed-1b-v2",
            "data": [
                {"object": "embedding", "index": 1, "embedding": [0.0, 1.0]},
                {"object": "embedding", "index": 0, "embedding": [1.0, 0.0]},
            ],
        })

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = NvidiaEmbeddingProvider(api_key="nvapi-test", timeout_seconds=12)

    vectors = provider.embed(["first", "second"], input_type="query")

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert seen["url"] == DEFAULT_NVIDIA_ENDPOINT
    assert seen["timeout"] == 12
    assert seen["authorization"] == "Bearer nvapi-test"
    assert seen["payload"]["input_type"] == "query"
    assert seen["payload"]["truncate"] == "NONE"
    assert seen["payload"]["modality"] == "text"


def test_hosted_provider_requires_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("SEMATIK_NVIDIA_EMBEDDINGS_URL", raising=False)
    with pytest.raises(EmbeddingConfigurationError, match="NVIDIA_API_KEY"):
        NvidiaEmbeddingProvider.from_env()


def test_self_hosted_provider_does_not_require_key():
    provider = NvidiaEmbeddingProvider(
        endpoint="http://localhost:8000/v1/embeddings",
        model="baai/bge-m3",
    )
    assert provider.api_key is None


def test_provider_rejects_inconsistent_embedding_dimensions(monkeypatch):
    def fake_urlopen(request, timeout):
        return _Response({
            "data": [
                {"index": 0, "embedding": [1.0, 0.0]},
                {"index": 1, "embedding": [1.0]},
            ],
        })

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = NvidiaEmbeddingProvider(api_key="nvapi-test")

    with pytest.raises(EmbeddingResponseError, match="inconsistent dimensions"):
        provider.embed(["first", "second"], input_type="passage")


class _FakeProvider:
    provider_name = "fake"
    model = "fake-embed-v1"

    def __init__(self):
        self.calls = []

    def embed(self, texts, *, input_type):
        self.calls.append((list(texts), input_type))
        if input_type == "query":
            return [[1.0, 0.0]]
        return [
            [0.95, 0.05],
            [0.0, 1.0],
            [0.7, 0.3],
        ]


def test_rank_semantic_candidates_uses_query_and_passage_modes():
    provider = _FakeProvider()
    concepts = {
        "land_value": "assessed land value for a property",
        "owner_name": "name of a person or organization holding title",
        "assessed_value": "assessor-determined taxable value",
    }

    ranked = rank_semantic_candidates(
        "legacy field stores the assessor's land value",
        concepts,
        provider,
        top_k=2,
    )

    assert [match.concept for match in ranked] == ["land_value", "assessed_value"]
    assert ranked[0].score > ranked[1].score
    assert ranked[0].provider == "fake"
    assert ranked[0].model == "fake-embed-v1"
    assert len(ranked[0].source_digest) == 16
    assert provider.calls[0][1] == "query"
    assert provider.calls[1][1] == "passage"


def test_similarity_score_is_not_promoted_to_confidence():
    provider = _FakeProvider()
    match = rank_semantic_candidates(
        "land value",
        {"land_value": "assessed land value"},
        provider,
        top_k=1,
    )[0]

    assert hasattr(match, "score")
    assert not hasattr(match, "confidence")
