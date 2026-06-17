# ACME Server Design — Certifactory

## Overview

Add an ACME (RFC 8555) server to Certifactory so automated clients like certbot, Caddy, and other ACME-compatible tools can request and obtain certificates through the standard ACME protocol. This is an additive feature — all existing capabilities (web UI, REST API, MCP server, approval workflows) remain unchanged.

ACME-issued certificates are stored in the same `certificates` table as all other certs and are visible in the normal Certificates list.

## Architecture

The ACME server is embedded in the existing FastAPI backend, following the same pattern as the MCP server. It registers as a new router with two URL schemes:

- `/acme/directory` — uses the configured default CA
- `/acme/<ca_id>/directory` — targets a specific CA

Both share the same implementation — the CA ID is resolved from the URL path or the default setting.

### Authentication

ACME uses its own key-based authentication scheme (not JWT or API tokens). Each client generates an account key pair locally. Every ACME request is a JWS (JSON Web Signature) signed with the client's private account key. Certifactory verifies the signature using the stored public key.

There is no integration with the existing Certifactory auth system — ACME has its own identity model defined by the RFC.

### Certificate Issuance

When an ACME order is finalized, the server calls the existing `CertificateService.submit_csr()` to create the certificate record, then auto-approves it via `CertificateService.approve()` with `_skip_self_check=True`. The challenge validation serves as the authorization — no manual approval is needed.

ACME-issued certificates are attributed to a system user (`acme-service`) that is auto-created on first ACME use.

## Database Models

### `acme_accounts`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Account identifier |
| jwk | JSON | Account public key (JWK format) |
| jwk_thumbprint | String, unique | SHA-256 thumbprint of the JWK for fast lookup |
| contact | JSON | List of contact URIs (e.g., `["mailto:admin@example.com"]`) |
| status | String | `active`, `deactivated`, `revoked` |
| created_at | DateTime | |
| updated_at | DateTime | |

### `acme_orders`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Order identifier |
| account_id | FK → acme_accounts | Owning account |
| ca_id | FK → certificate_authorities | Issuing CA |
| status | String | `pending`, `ready`, `processing`, `valid`, `invalid` |
| identifiers | JSON | List of `{"type": "dns", "value": "example.com"}` |
| not_before | DateTime, nullable | Requested start of validity |
| not_after | DateTime, nullable | Requested end of validity |
| certificate_id | FK → certificates, nullable | Set when order is finalized |
| expires | DateTime | Order expiry (e.g., 7 days from creation) |
| created_at | DateTime | |

### `acme_authorizations`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Authorization identifier |
| order_id | FK → acme_orders | Parent order |
| identifier_type | String | `dns` |
| identifier_value | String | The domain name |
| status | String | `pending`, `valid`, `invalid`, `deactivated`, `expired`, `revoked` |
| challenges | JSON | List of challenge objects (see below) |
| expires | DateTime | Authorization expiry |
| created_at | DateTime | |

**Challenge object structure** (stored in the `challenges` JSON array):

```json
{
  "type": "http-01",
  "token": "random-base64url-string",
  "status": "pending",
  "validated": null,
  "error": null
}
```

Each authorization contains up to three challenges (one per supported type). The client chooses which one to complete.

## Alembic Migration

A single migration creates all three tables. No existing tables are modified. Uses `sa.String()` for status columns (not enums) to avoid PostgreSQL enum type issues, consistent with the templates migration pattern.

## ACME Endpoints

All endpoints follow RFC 8555. Every POST is a JWS. Every response includes a `Replay-Nonce` header.

### Directory & Nonce

| Method | Path | Description |
|--------|------|-------------|
| GET | `/acme/directory` | Returns ACME directory with endpoint URLs |
| GET | `/acme/<ca_id>/directory` | Same, for a specific CA |
| HEAD/GET | `/acme/new-nonce` | Returns a fresh nonce |

The directory response includes URLs for `newNonce`, `newAccount`, `newOrder`, `revokeCert`, and `keyChange`.

### Account Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/acme/new-account` | Register or look up an account |

Registration creates the account if it doesn't exist. If the JWK already exists (matched by thumbprint), returns the existing account. The `onlyReturnExisting` flag allows lookup without creation.

When `acme_registration_open` is `false`, new account creation is rejected — only existing accounts can operate.

### Order Lifecycle

| Method | Path | Description |
|--------|------|-------------|
| POST | `/acme/new-order` | Create an order for a set of domain identifiers |
| POST | `/acme/order/<order_id>` | Get order status |
| POST | `/acme/order/<order_id>/finalize` | Submit CSR to finalize |
| GET | `/acme/order/<order_id>/cert` | Download issued certificate chain |

### Authorization & Challenges

| Method | Path | Description |
|--------|------|-------------|
| POST | `/acme/authz/<authz_id>` | Get authorization details and challenges |
| POST | `/acme/challenge/<authz_id>/<challenge_type>` | Client signals readiness |

### Certificate Revocation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/acme/revoke-cert` | Revoke a certificate by PEM |

## JWS Validation

Every ACME POST request body is a JWS (RFC 7515) with a flattened JSON serialization:

```json
{
  "protected": "base64url-encoded-header",
  "payload": "base64url-encoded-payload",
  "signature": "base64url-encoded-signature"
}
```

The protected header contains:
- `alg` — signing algorithm (RS256, ES256, etc.)
- `nonce` — replay protection nonce
- `url` — the request URL (prevents request reuse across endpoints)
- `jwk` — account public key (only for `newAccount`)
- `kid` — account URL (for all other requests, mutually exclusive with `jwk`)

**Validation steps:**
1. Decode protected header
2. Verify `url` matches the request URL
3. Consume the `nonce` (reject if invalid/reused)
4. For `newAccount`: extract JWK from header, compute thumbprint
5. For other endpoints: look up account by `kid` URL, get stored JWK
6. Verify signature using the JWK
7. Decode payload

## Nonce Management

Nonces are stored in-memory as a set with a TTL (e.g., 1 hour). Each nonce is consumed on use. If the server restarts, all nonces are invalidated — clients receive a `badNonce` error and automatically retry with a fresh nonce. This is expected behavior per the RFC.

Every ACME response includes a new `Replay-Nonce` header.

## Challenge Validation

### HTTP-01

1. Server generates a random `token` (base64url, 32 bytes)
2. Client must serve `{token}.{account_key_thumbprint}` at `http://{domain}/.well-known/acme-challenge/{token}`
3. On client readiness signal, server makes an HTTP GET to that URL
4. Validates response body matches `{token}.{account_key_thumbprint}`
5. Uses `httpx` (already a dependency) for the outbound request

### DNS-01

1. Server generates the same `token`
2. Client must create a DNS TXT record at `_acme-challenge.{domain}` containing `base64url(sha256({token}.{account_key_thumbprint}))`
3. On client readiness signal, server does a DNS TXT lookup
4. Validates one of the TXT records matches the expected value
5. Requires `dnspython` as a new dependency
6. This is the only challenge type that supports wildcard certificates

### TLS-ALPN-01

1. Server generates the same `token`
2. Client must serve a self-signed certificate on port 443 with:
   - `acme-tls/1` ALPN protocol
   - `acmeIdentifier` extension (OID 1.3.6.1.5.5.7.1.31) containing `sha256({token}.{account_key_thumbprint})`
   - SAN matching the domain being validated
3. On client readiness signal, server opens a TLS connection to `{domain}:443` with `acme-tls/1` ALPN
4. Validates the certificate's `acmeIdentifier` extension
5. Uses Python's `ssl` standard library — no new dependency

### Validation Flow (all types)

1. Client POSTs to `/acme/challenge/<authz_id>/<challenge_type>` with `{}`
2. Challenge status → `processing`
3. Server performs the validation (async)
4. On success: challenge → `valid`, authorization → `valid`. If all authorizations valid, order → `ready`
5. On failure: challenge → `invalid` with error detail. Client can retry.

## Order Finalization

1. Client POSTs a CSR (base64url-encoded DER) to `/acme/order/<order_id>/finalize`
2. Server validates:
   - Order status is `ready`
   - CSR is well-formed
   - CSR's SANs/CN match the order's identifiers exactly
3. Order → `processing`
4. Server converts DER CSR to PEM and calls `CertificateService.submit_csr()` with the order's CA
5. If the CA doesn't auto-approve, the server calls `CertificateService.approve()` with `_skip_self_check=True`
6. Links the certificate to the order, order → `valid`
7. Client retrieves the cert chain from `/acme/order/<order_id>/cert`

The cert endpoint returns the end-entity certificate followed by the CA chain, concatenated as PEM — standard ACME behavior.

## Settings

New settings in the existing key-value settings table (category: `acme`):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `acme_enabled` | bool | false | Global ACME kill switch |
| `acme_default_ca_id` | string | "" | CA ID for `/acme/directory`. Empty = ACME disabled for default path |
| `acme_registration_open` | bool | true | Allow new account registration |
| `acme_allowed_domains` | string | "" | Comma-separated domain patterns. Empty = all allowed. Supports `*.example.com` |

These appear as a new "ACME" category on the Settings page with appropriate UI controls (toggles for bools, CA dropdown for default CA, text input for allowed domains).

## Nginx Proxy

Add a location block for `/acme` in the nginx config template, proxying to the backend:

```nginx
location /acme {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Dependencies

- `dnspython` — for DNS-01 challenge validation (DNS TXT record lookup)
- No other new dependencies. `httpx` (HTTP-01), `ssl` (TLS-ALPN-01), and `cryptography` (JWS) are already available.

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/models/acme.py` | Create | AcmeAccount, AcmeOrder, AcmeAuthorization models |
| `backend/app/models/__init__.py` | Modify | Export new models |
| `backend/app/services/acme_service.py` | Create | ACME business logic (accounts, orders, challenges, JWS validation, nonces) |
| `backend/app/routers/acme.py` | Create | All ACME HTTP endpoints |
| `backend/app/schemas/acme.py` | Create | Pydantic models for ACME request/response |
| `backend/app/services/settings_service.py` | Modify | Add ACME settings definitions |
| `backend/app/main.py` | Modify | Register ACME router |
| `backend/requirements.txt` | Modify | Add `dnspython` |
| `backend/alembic/versions/...` | Create | Migration for 3 new tables |
| `proxy/nginx.conf.template` | Modify | Add `/acme` location block |
| `frontend/src/pages/Settings.jsx` | Modify | Add ACME category label |
| `frontend/src/pages/Docs.jsx` | Modify | Add ACME documentation tab |
| `backend/tests/test_acme.py` | Create | Tests for ACME endpoints |

## Error Handling

ACME errors follow RFC 8555 Section 6.7 — JSON responses with `type`, `detail`, and `status`:

```json
{
  "type": "urn:ietf:params:acme:error:malformed",
  "detail": "Request body is not valid JWS",
  "status": 400
}
```

Standard error types used: `badNonce`, `malformed`, `unauthorized`, `accountDoesNotExist`, `orderNotReady`, `badCSR`, `rejectedIdentifier`, `connection` (challenge validation failure).

## Testing

- JWS creation/validation with test key pairs
- Account registration and lookup
- Order lifecycle (create → authorize → finalize → download)
- Challenge token generation and validation logic (mock outbound HTTP/DNS/TLS)
- Nonce management (create, consume, reject reuse)
- Domain restriction enforcement
- Registration restriction enforcement
- CSR/identifier matching validation
