"""ADR-0006 section 8: egress is fail-closed on the embedding path (#39).

Every denial test also asserts the provider was never called: a gate that
reports a denial after the text has already been sent is not a gate."""

import pytest

from sematik.egress import (DataClassification, EgressDestination, EgressPolicy,
                            destination_for_endpoint, is_known_hosted_endpoint)
from sematik.embeddings import (EgressDeniedError, EmbeddingConfigurationError,
                                NvidiaEmbeddingProvider, rank_semantic_candidates)

CONCEPTS = {"Assessment": "a taxable conclusion for a property interest"}
CONFIDENTIAL_TEXT = "APN 123-45-678 owner Jane Q. Public assessed 912,000"
POLICY = EgressPolicy.conservative_government_default()


class _Spy(NvidiaEmbeddingProvider):
    """Real provider config (so destination derivation is real); embed() never
    touches the network and records what would have been sent."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.sent = []

    def embed(self, texts, *, input_type):
        self.sent.append((input_type, list(texts)))
        return [[1.0, 0.0] for _ in texts]


class _Bare:
    """A provider that declares no destination at all."""
    provider_name, model = "bare", "bare-1"

    def __init__(self):
        self.sent = []

    def embed(self, texts, *, input_type):
        self.sent.append(list(texts))
        return [[1.0, 0.0] for _ in texts]


def _rank(provider, *, classification, policy=POLICY, text=CONFIDENTIAL_TEXT):
    return rank_semantic_candidates(text, CONCEPTS, provider, egress_policy=policy,
                                    classification=classification, purpose="test")


HOSTED = dict(api_key="nvapi-x")   # default endpoint: integrate.api.nvidia.com
LOOPBACK = dict(endpoint="http://127.0.0.1:8000/v1/embeddings")
INTERNAL_HTTPS = "https://embed.county.internal/v1/embeddings"


@pytest.mark.parametrize("cls", [DataClassification.INTERNAL,
                                 DataClassification.CONFIDENTIAL,
                                 DataClassification.RESTRICTED])
def test_nonpublic_data_is_denied_for_hosted_endpoint_and_nothing_is_sent(cls):
    p = _Spy(**HOSTED)
    assert p.egress_destination is EgressDestination.HOSTED_EXTERNAL
    with pytest.raises(EgressDeniedError, match="not approved for hosted_external"):
        _rank(p, classification=cls)
    assert p.sent == []


def test_public_data_may_reach_hosted_endpoint_and_decision_basis_is_recorded():
    p = _Spy(**HOSTED)
    match = _rank(p, classification=DataClassification.PUBLIC, text="land value")[0]
    assert (match.classification, match.egress_destination) == ("public", "hosted_external")
    assert [t for t, _ in p.sent] == ["query", "passage"]


def test_loopback_endpoint_is_local_and_keeps_restricted_data_inside():
    p = _Spy(**LOOPBACK)
    assert p.egress_destination is EgressDestination.LOCAL
    _rank(p, classification=DataClassification.RESTRICTED)
    assert len(p.sent) == 2


def test_self_hosted_requires_explicit_attestation_otherwise_fails_closed():
    attested = _Spy(endpoint=INTERNAL_HTTPS, self_hosted=True)
    unattested = _Spy(endpoint=INTERNAL_HTTPS)
    assert attested.egress_destination is EgressDestination.SELF_HOSTED
    assert unattested.egress_destination is EgressDestination.HOSTED_EXTERNAL
    _rank(attested, classification=DataClassification.RESTRICTED)
    with pytest.raises(EgressDeniedError):
        _rank(unattested, classification=DataClassification.RESTRICTED)
    assert unattested.sent == []


def test_known_hosted_service_cannot_be_attested_as_self_hosted():
    with pytest.raises(EmbeddingConfigurationError, match="cannot be attested"):
        NvidiaEmbeddingProvider(api_key="nvapi-x", self_hosted=True)


def test_provider_that_declares_no_destination_is_treated_as_external():
    p = _Bare()
    with pytest.raises(EgressDeniedError):
        _rank(p, classification=DataClassification.INTERNAL)
    assert p.sent == []
    _rank(p, classification=DataClassification.PUBLIC)   # public still permitted


def test_empty_policy_denies_everything_even_public_to_local():
    with pytest.raises(EgressDeniedError):
        _rank(_Spy(**LOOPBACK), classification=DataClassification.PUBLIC,
              policy=EgressPolicy())


def test_stricter_deployment_policy_is_honored():
    local_only = EgressPolicy(allowed={EgressDestination.LOCAL:
                                       frozenset(DataClassification)})
    _rank(_Spy(**LOOPBACK), classification=DataClassification.RESTRICTED, policy=local_only)
    attested = _Spy(endpoint=INTERNAL_HTTPS, self_hosted=True)
    with pytest.raises(EgressDeniedError):
        _rank(attested, classification=DataClassification.PUBLIC, policy=local_only)
    assert attested.sent == []


def test_policy_and_classification_are_required_not_defaulted():
    p = _Spy(**LOOPBACK)
    with pytest.raises(TypeError):
        rank_semantic_candidates("x", CONCEPTS, p)
    with pytest.raises(TypeError, match="DataClassification"):
        rank_semantic_candidates("x", CONCEPTS, p, egress_policy=POLICY,
                                 classification="public", purpose="t")
    with pytest.raises(TypeError, match="EgressPolicy"):
        rank_semantic_candidates("x", CONCEPTS, p, egress_policy={"public"},
                                 classification=DataClassification.PUBLIC, purpose="t")
    assert p.sent == []


def test_concept_text_is_also_gated_not_only_the_query():
    # Same classification governs everything sent in the call, so a restricted
    # Domain Pack cannot leak just because the query text looked harmless.
    p = _Spy(**HOSTED)
    with pytest.raises(EgressDeniedError, match="query|concept passages"):
        _rank(p, classification=DataClassification.CONFIDENTIAL, text="land value")
    assert p.sent == []


@pytest.mark.parametrize("endpoint,attested,expected", [
    ("http://localhost:8000/v1", False, EgressDestination.LOCAL),
    ("http://127.0.0.1/v1", False, EgressDestination.LOCAL),
    ("https://integrate.api.nvidia.com/v1/embeddings", False, EgressDestination.HOSTED_EXTERNAL),
    ("https://integrate.api.nvidia.com/v1/embeddings", True, EgressDestination.HOSTED_EXTERNAL),
    (INTERNAL_HTTPS, False, EgressDestination.HOSTED_EXTERNAL),
    (INTERNAL_HTTPS, True, EgressDestination.SELF_HOSTED),
    ("not a url", True, EgressDestination.HOSTED_EXTERNAL),   # unparseable never gets trusted
    ("https://", True, EgressDestination.HOSTED_EXTERNAL),
    ("", False, EgressDestination.HOSTED_EXTERNAL),
])
def test_destination_is_derived_from_the_endpoint(endpoint, attested, expected):
    assert destination_for_endpoint(endpoint, attested_self_hosted=attested) is expected


def test_lookalike_hosts_are_not_mistaken_for_known_hosted_services():
    assert is_known_hosted_endpoint("https://integrate.api.nvidia.com/x")
    assert not is_known_hosted_endpoint("https://notnvidia.com/x")
    assert not is_known_hosted_endpoint("https://nvidia.com.evil.example/x")
