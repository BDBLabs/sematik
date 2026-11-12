"""Real FastAPI auth boundary tests with a test-only credential adapter."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.auth import get_identity_provider, require_action
from api.main import app
from sematik.access import Origin, Principal, ResourceScope, authorize


class CredentialProvider:
    def verify(self, credential: str) -> Principal | None:
        if credential not in {"valid", "analyst", "expired", "internal", "wrong-issuer"}:
            return None
        roles = frozenset({"analyst", "conversion_operator", "tenant_reader"})
        if credential == "analyst":
            roles = frozenset({"analyst"})
        return Principal(
            actor_id="actor-a", tenant_id="tenant-a", roles=roles,
            issuer="" if credential == "wrong-issuer" else "test-verifier",
            authentication_method="opaque-test-token",
            expires_at=datetime.now(UTC) + (
                timedelta(seconds=-1) if credential == "expired" else timedelta(minutes=5)
            ),
            origin=Origin.INTERNAL if credential == "internal" else Origin.EXTERNAL,
        )


@pytest.fixture
def client():
    old = app.dependency_overrides.get(get_identity_provider)
    app.dependency_overrides[get_identity_provider] = lambda: CredentialProvider()
    with TestClient(app) as test_client:
        yield test_client
    if old is None:
        app.dependency_overrides.pop(get_identity_provider, None)
    else:
        app.dependency_overrides[get_identity_provider] = old


@pytest.mark.parametrize("path,method", [
    ("/api/v1/profile", "POST"),
    ("/api/v1/hypotheses", "POST"),
    ("/api/v1/candidates", "POST"),
    ("/api/v1/mapping/digest", "POST"),
    ("/api/v1/compile", "POST"),
    ("/api/v1/compile-sql", "POST"),
    ("/api/v1/execute", "POST"),
    ("/api/v1/reconcile/population", "POST"),
    ("/api/v1/reconcile/records", "POST"),
    ("/api/v1/reconcile/semantic", "POST"),
    ("/api/v1/entropy/concept", "POST"),
    ("/api/v1/entropy/semantic", "POST"),
    ("/api/v1/entropy/semantic-flagged", "POST"),
    ("/api/v1/fixture/legacy_parcels", "GET"),
    ("/api/v1/fixture/demo-mapping", "GET"),
    ("/api/v1/fixture/demo-steps", "GET"),
    ("/api/v1/tenants/tenant-a/access", "GET"),
])
def test_every_data_route_rejects_unauthenticated(client: TestClient, path: str, method: str):
    response = client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code == 401
    assert response.json() == {"detail": "authentication required"}


def test_default_production_entry_fails_closed(monkeypatch):
    monkeypatch.setenv("SEMATIK_TEST_AUTH", "true")
    assert get_identity_provider() is None  # no environment switch to a fixture provider
    with TestClient(app) as production_client:
        assert production_client.get("/api/v1/health").status_code == 200
        response = production_client.post("/api/v1/execute", json={})
        assert response.status_code == 503
        assert response.json() == {"detail": "authentication unavailable"}
        assert production_client.get("/api/v1/fixture/demo-mapping").status_code == 503


@pytest.mark.parametrize("credential", ["invalid", "expired", "wrong-issuer"])
def test_invalid_or_expired_credentials_do_not_authenticate(client: TestClient, credential: str):
    response = client.get("/api/v1/tenants/tenant-a/access",
                          headers={"Authorization": f"Bearer {credential}"})
    assert response.status_code == 401
    assert "actor-a" not in response.text


def test_actor_cannot_choose_another_tenant_or_spoof_headers(client: TestClient):
    headers = {"Authorization": "Bearer valid", "X-Actor": "attacker",
               "X-Tenant-ID": "tenant-b", "X-Role": "conversion_operator"}
    own = client.get("/api/v1/tenants/tenant-a/access", headers=headers)
    assert own.status_code == 200
    assert own.json() == {"actor_id": "actor-a", "tenant_id": "tenant-a"}
    other = client.get("/api/v1/tenants/tenant-b/access", headers=headers)
    assert other.status_code == 404
    assert "tenant-b" not in other.text


def test_body_cannot_escalate_role_or_approval(client: TestClient):
    response = client.post("/api/v1/execute", headers={"Authorization": "Bearer analyst"},
                           json={"tenant_id": "tenant-a", "roles": ["conversion_operator"],
                                 "approved_by": "administrator", "approval_ref": "forged"})
    assert response.status_code == 403
    assert "administrator" not in response.text


def test_role_without_resource_permission_is_denied(client: TestClient):
    response = client.get("/api/v1/tenants/tenant-a/access",
                          headers={"Authorization": "Bearer analyst"})
    assert response.status_code == 403
    assert "tenant-a" not in response.text


def test_internal_origin_has_no_implicit_api_grant(client: TestClient):
    response = client.get("/api/v1/tenants/tenant-a/access",
                          headers={"Authorization": "Bearer internal"})
    assert response.status_code == 403
    assert not authorize(None, "tenant:read", ResourceScope("tenant-a"))


def test_missing_policy_denies_through_http():
    isolated_app = FastAPI()

    @isolated_app.get("/protected", dependencies=[Depends(require_action("institution:adjudicate"))])
    def protected():
        return {"should_not_be_visible": True}

    isolated_app.dependency_overrides[get_identity_provider] = lambda: CredentialProvider()
    with TestClient(isolated_app) as isolated_client:
        response = isolated_client.get("/protected", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 403
    assert response.json() == {"detail": "access denied"}


def test_missing_policy_and_owner_scope_deny():
    principal = CredentialProvider().verify("valid")
    assert principal is not None
    assert not authorize(principal, "institution:adjudicate", ResourceScope("tenant-a"))
    assert not authorize(principal, "tenant:read", ResourceScope("tenant-b"))
    assert not authorize(principal, "tenant:read", ResourceScope(
        "tenant-a", owner_actor_id="someone-else", owner_only=True))


def test_cors_is_explicit(client: TestClient):
    headers = {"Access-Control-Request-Method": "POST",
               "Access-Control-Request-Headers": "authorization,content-type"}
    allowed = client.options("/api/v1/profile",
                             headers={**headers, "Origin": "http://localhost:5173"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    denied = client.options("/api/v1/profile",
                            headers={**headers, "Origin": "https://hostile.example"})
    assert "access-control-allow-origin" not in denied.headers


def test_audit_logs_exclude_credential_and_payload(client: TestClient, caplog):
    caplog.set_level(logging.INFO, logger="sematik.authorization")
    response = client.post("/api/v1/execute", headers={"Authorization": "Bearer invalid"},
                           json={"rows": [{"private_note": "SECRET_ROW_CONTENT"}]})
    assert response.status_code == 401
    assert "invalid" not in caplog.text
    assert "SECRET_ROW_CONTENT" not in caplog.text
    assert "result=deny" in caplog.text
