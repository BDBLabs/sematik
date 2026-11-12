"""Fail-closed FastAPI authentication boundary.

Production has no implicit identity provider. A deployment must explicitly
integrate a verified provider (for example configured OIDC/JWT validation)
before protected operations become available. Tests inject a verifier through
FastAPI dependency overrides; no environment flag enables test credentials.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request

from sematik.access import Principal, ResourceScope, authorize

_LOG = logging.getLogger("sematik.authorization")
_BEARER = re.compile(r"Bearer ([A-Za-z0-9._~+/-]+=*)\Z", re.IGNORECASE)


class IdentityProvider(Protocol):
    def verify(self, credential: str) -> Principal | None:
        """Validate credential cryptographically or against a trusted store."""


def get_identity_provider() -> IdentityProvider | None:
    """No production provider is configured in PR 1: protected routes deny."""
    return None


def _audit(request: Request, *, result: str, reason: str,
           principal: Principal | None = None) -> None:
    # A server-generated ID prevents caller-supplied log-injection identifiers.
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
    _LOG.info(
        "authorization request_id=%s method=%s path=%s actor=%s tenant=%s result=%s reason=%s",
        request_id, request.method, getattr(request.scope.get("route"), "path", "<unmatched>"),
        principal.actor_id if principal else "-",
        principal.tenant_id if principal else "-", result, reason,
    )


def authenticated_principal(
    request: Request,
    provider: Annotated[IdentityProvider | None, Depends(get_identity_provider)],
) -> Principal:
    if provider is None:
        _audit(request, result="deny", reason="provider_unconfigured")
        raise HTTPException(503, "authentication unavailable")
    match = _BEARER.fullmatch(request.headers.get("authorization", ""))
    if match is None:
        _audit(request, result="deny", reason="credential_missing_or_invalid")
        raise HTTPException(401, "authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        principal = provider.verify(match.group(1))
    except Exception:  # noqa: BLE001 - an untrusted provider failure must deny generically
        _audit(request, result="deny", reason="credential_verification_failed")
        raise HTTPException(401, "authentication required", headers={"WWW-Authenticate": "Bearer"}) from None
    if principal is None or not isinstance(principal, Principal):
        _audit(request, result="deny", reason="credential_verification_failed")
        raise HTTPException(401, "authentication required", headers={"WWW-Authenticate": "Bearer"})
    # A verified identity still needs role, tenant, issuer, expiry and origin.
    if not principal.actor_id or not principal.tenant_id or not principal.issuer or not principal.authentication_method:
        _audit(request, result="deny", reason="identity_incomplete")
        raise HTTPException(401, "authentication required", headers={"WWW-Authenticate": "Bearer"})
    if principal.expires_at.tzinfo is None or principal.expires_at <= datetime.now(UTC):
        _audit(request, result="deny", reason="credential_expired")
        raise HTTPException(401, "authentication required", headers={"WWW-Authenticate": "Bearer"})
    request.state.principal = principal
    return principal


def require_action(action: str):
    """FastAPI dependency enforcing a permission for the principal's tenant.

    Routes with stored resources must additionally check the resource's tenant
    after trusted lookup. PR 1 contains no tenant-owned resource endpoints.
    """
    def check(request: Request,
              principal: Annotated[Principal, Depends(authenticated_principal)]) -> Principal:
        if not authorize(principal, action, ResourceScope(principal.tenant_id)):
            _audit(request, result="deny", reason="permission_or_identity", principal=principal)
            raise HTTPException(403, "access denied")
        _audit(request, result="allow", reason=action, principal=principal)
        return principal

    return check


def authorize_resource(request: Request, principal: Principal, action: str,
                       resource: ResourceScope) -> None:
    if not authorize(principal, action, resource):
        _audit(request, result="deny", reason="resource_scope", principal=principal)
        # Hide whether a different tenant's resource exists.
        raise HTTPException(404, "not found")
    _audit(request, result="allow", reason=action, principal=principal)
