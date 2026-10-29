"""Data-egress policy primitives for Discovery-plane external services.

The default policy is intentionally conservative for government/customer data:
external hosted services are allowed only for PUBLIC content unless a deployment
explicitly supplies a different reviewed policy. Self-hosted and local routes
remain separately classified so deployments can keep protected evidence inside
their trust boundary.
"""

from __future__ import annotations

import hashlib
import ipaddress
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlparse


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class EgressDestination(str, Enum):
    LOCAL = "local"
    SELF_HOSTED = "self_hosted"
    HOSTED_EXTERNAL = "hosted_external"


@dataclass(frozen=True)
class EgressRequest:
    classification: DataClassification
    destination: EgressDestination
    content_digest: str
    purpose: str
    redacted: bool = False

    def __post_init__(self) -> None:
        if len(self.content_digest) != 64:
            raise ValueError("egress request requires a full SHA-256 digest")
        try:
            int(self.content_digest, 16)
        except ValueError as exc:
            raise ValueError("content_digest must be hexadecimal") from exc
        if not self.purpose.strip():
            raise ValueError("egress purpose is required")

    @classmethod
    def from_text(
        cls,
        *,
        text: str,
        classification: DataClassification,
        destination: EgressDestination,
        purpose: str,
        redacted: bool = False,
    ) -> "EgressRequest":
        return cls(
            classification=classification,
            destination=destination,
            content_digest=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            purpose=purpose,
            redacted=redacted,
        )


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class EgressPolicy:
    """Explicit allowlist by destination.

    SELF_HOSTED means inside the customer-controlled trust boundary.
    Deployments may replace this with a customer-approved policy, but they must
    not infer permission from the presence of an API key.
    """

    allowed: Mapping[EgressDestination, frozenset[DataClassification]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        frozen = {
            destination: frozenset(classes)
            for destination, classes in self.allowed.items()
        }
        object.__setattr__(self, "allowed", MappingProxyType(frozen))

    @classmethod
    def conservative_government_default(cls) -> "EgressPolicy":
        all_classes = frozenset(DataClassification)
        return cls(
            allowed={
                EgressDestination.LOCAL: all_classes,
                EgressDestination.SELF_HOSTED: all_classes,
                EgressDestination.HOSTED_EXTERNAL: frozenset(
                    {DataClassification.PUBLIC}
                ),
            }
        )

    def authorize(self, request: EgressRequest) -> EgressDecision:
        allowed_classes = self.allowed.get(request.destination, frozenset())
        if request.classification not in allowed_classes:
            return EgressDecision(
                allowed=False,
                reason=(
                    f"{request.classification.value} data is not approved for "
                    f"{request.destination.value}"
                ),
            )
        return EgressDecision(
            allowed=True,
            reason=(
                f"{request.classification.value} data approved for "
                f"{request.destination.value}"
            ),
        )


def credential_transport_allowed(endpoint: str) -> bool:
    """Credentials may travel over HTTPS or cleartext loopback only."""
    parsed = urlparse(endpoint)
    if not parsed.hostname:
        return False
    if parsed.scheme == "https":
        return True
    if parsed.scheme != "http":
        return False
    return _is_loopback(parsed.hostname)


def endpoint_allows_credentials(endpoint: str) -> bool:
    """Credentials may use HTTPS or cleartext loopback only.

    This deliberately rejects API-key transmission over ordinary HTTP. Loopback
    is allowed for local development/self-hosted NIMs. Single implementation
    shared with the embeddings provider (no duplicated transport rule).
    """
    return credential_transport_allowed(endpoint)


_KNOWN_HOSTED_SUFFIXES = ("nvidia.com",)


def _is_loopback(hostname: str) -> bool:
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def is_known_hosted_endpoint(endpoint: str) -> bool:
    """True for third-party hosted services a deployment cannot attest as its own."""
    host = (urlparse(endpoint).hostname or "").lower()
    return any(host == s or host.endswith("." + s) for s in _KNOWN_HOSTED_SUFFIXES)


def destination_for_endpoint(endpoint: str, *, attested_self_hosted: bool = False
                             ) -> EgressDestination:
    """Derive the egress destination from the endpoint, never from the caller.

    Loopback is LOCAL. Anything else is HOSTED_EXTERNAL unless the deployment
    owner explicitly attests it lies inside the customer-controlled trust
    boundary, and a known third-party hosted service can never be attested.
    Unknown or unattested therefore fails closed to the strictest route.
    """
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower()
    if not host:
        return EgressDestination.HOSTED_EXTERNAL   # unparseable: fail closed, whatever is attested
    if _is_loopback(host):
        return EgressDestination.LOCAL
    if attested_self_hosted and not is_known_hosted_endpoint(endpoint):
        return EgressDestination.SELF_HOSTED
    return EgressDestination.HOSTED_EXTERNAL
