# Phase 1 identity and authorization boundary

Status: PR 1 implementation, limited foundation. This document does not certify
Sematik for client data. ADR-0008 and ADR-0009 remain Proposed.

## Request boundary

`/api/v1/health` is public for hosting probes. Every other current `/api/v1`
route requires a bearer credential verified by an `IdentityProvider` and an
explicit role action. This includes fixture, profiling, hypothesis, mapping,
compilation, execution, reconciliation, and entropy routes because their
payloads or results may contain institutional content. Static UI files remain
public but cannot use protected API routes without an authenticated provider.

The default production entry point has **no provider**. Protected routes return
503 `authentication unavailable`; setting a test-auth environment variable or
an arbitrary identity header does not enable one. A future deployment adapter
must verify a configured OIDC/JWT issuer and audience or an equivalent trusted
credential mechanism, then return a `Principal` with actor, tenant, roles,
issuer, method, expiry, and optional permission scope. The application does not
mint passwords or accept actor/tenant/roles from request bodies or untrusted
headers. A provider must fail closed on invalid or expired credentials.
The current boundary checks issuer presence and expiry; issuer trust and
audience validation require that future concrete provider.

Tests inject a fixture verifier through FastAPI's dependency override and use
bearer credentials through the actual API path. That test verifier lives only
under `tests/`; the Docker runtime copies only `tests/fixtures/`. No production
configuration flag selects it. The positive conversion tests therefore prove
that the algorithm still works behind the request boundary, not that production
authentication is configured.

The supported role-action matrix is intentionally narrow:

| Role | Actions |
|---|---|
| `analyst` | `discovery:analyze`, `conversion:plan`, `conversion:reconcile` |
| `conversion_operator` | `conversion:execute` |
| `tenant_reader` | `tenant:read` |

No general administrator role is implied. `authorize()` denies a missing or
expired principal, unknown action, different resource tenant, failed owner
scope, and an internal/test/maintenance origin without a separately designed
grant. The `/api/v1/tenants/{tenant_id}/access` route exercises the resource
tenant check and returns 404 for the wrong tenant without revealing whether
it exists. Existing conversion routes have **no stored resource identity**;
their action checks use the authenticated tenant but cannot establish that
arbitrary submitted rows belong to that tenant. They must not be described as
fully tenant isolated. The storage and trusted provenance gates are Priority 0
follow-ups.

All authorization outcomes log a server-generated request ID, method, route
template, actor/tenant IDs when authenticated, decision and reason. Credentials,
source rows, request bodies, arbitrary URL path values and provider responses
are not logged by this boundary. Actor and tenant identifiers are escaped in
line-oriented logs to prevent control-character injection.
`SEMATIK_ALLOWED_ORIGINS` is a comma-separated
list of exact browser origins; the default allows local development on ports
5173 and no wildcard. CORS is not an authorization mechanism.

## Execution origins and remaining exposures

The API represents authenticated external calls. Domain functions remain
callable in process; no internal or maintenance principal is silently minted.
Internal services and migrations will need explicit, narrow service grants when
they become API consumers. Test credentials are only supplied by test code.

The current API still accepts caller-supplied `approved_by`, `approval_ref`,
`evidence_refs`, `golden_plan_digest`, and `require_golden`; the compiler's
verified approval token is optional. Authentication of the caller **does not**
turn these fields into governed Control-plane approval. The Control store lacks
the required reference, revocation and tenant enforcement. A later Priority 0
PR must bind approval to trusted durable state before client-data conversion.
Hosted embedding egress, durable evidence, derivative rights, retention and
withdrawal are likewise outside this PR. Do not send client data to the
existing stateless conversion endpoints while those gates are open.

This PR intentionally changes unauthenticated API behavior: a deployment with
no configured provider no longer runs the public conversion demo. The health
endpoint and static UI continue to load; protected calls fail closed. A future
synthetic-only demo may be exposed through a separately scoped policy, but no
test or demo bypass is enabled in production here.

AI-Model: gpt-6-sol
AI-Provider: OpenAI
AI-Tool: Codex
AI-Role: Author
