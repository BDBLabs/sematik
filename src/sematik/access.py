"""Tenant-scoped authorization policy; identity is supplied by a trusted adapter.

This module does not authenticate credentials or grant institutional approval.
Every service entry point must supply an authenticated context explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class Origin(str, Enum):
    EXTERNAL = "external"
    INTERNAL = "internal"
    TEST = "test"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class Principal:
    actor_id: str
    tenant_id: str
    roles: frozenset[str]
    issuer: str
    authentication_method: str
    expires_at: datetime
    scopes: frozenset[str] = field(default_factory=frozenset)
    origin: Origin = Origin.EXTERNAL


@dataclass(frozen=True)
class ResourceScope:
    tenant_id: str
    owner_actor_id: str | None = None
    owner_only: bool = False


# No catch-all administrator role. A verified identity receives only the
# operations explicitly assigned to its role by the deployment policy.
ROLE_ACTIONS: dict[str, frozenset[str]] = {
    "analyst": frozenset({"discovery:analyze", "conversion:plan", "conversion:reconcile"}),
    "conversion_operator": frozenset({"conversion:execute"}),
    "tenant_reader": frozenset({"tenant:read"}),
}


def authorize(principal: Principal | None, action: str, resource: ResourceScope) -> bool:
    """Deny missing, expired, cross-tenant, unscoped, or non-external access.

    Internal, maintenance and test callers need a separately designed scoped
    grant in a later PR; they do not inherit API privileges by being in-process.
    This is the policy check, not a replacement for authentication or future
    storage-level tenant filtering.
    """
    if principal is None or principal.origin is not Origin.EXTERNAL:
        return False
    if not principal.actor_id or not principal.tenant_id or not principal.issuer:
        return False
    if principal.expires_at.tzinfo is None or principal.expires_at <= datetime.now(UTC):
        return False
    if not resource.tenant_id or resource.tenant_id != principal.tenant_id:
        return False
    if resource.owner_only and resource.owner_actor_id != principal.actor_id:
        return False
    permitted = frozenset().union(*(ROLE_ACTIONS.get(role, frozenset()) for role in principal.roles))
    return action in permitted and (not principal.scopes or action in principal.scopes)
