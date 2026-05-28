# MCP Server Design — Certifactory

## Overview

Add an MCP (Model Context Protocol) server to Certifactory so AI agents can programmatically interact with the PKI infrastructure. The server is embedded in the existing FastAPI backend and exposes tools for reading PKI state and issuing certificates.

## Architecture

### Embedded in Backend

The MCP server is built directly into the FastAPI backend process. It:

- Calls the service layer (`CAService`, `CertificateService`, `CRLService`) directly
- Shares the same database session factory (`SessionLocal`)
- Uses the same models, schemas, and business logic as the REST API
- Mounts as a Streamable HTTP endpoint alongside the existing REST routes

### Transport

**Streamable HTTP** at `/mcp`. This is the modern MCP transport, replacing SSE. It works for both local and remote access and integrates naturally with the existing FastAPI HTTP server.

The endpoint is mounted on the FastAPI app using the MCP Python SDK's ASGI integration.

### Authentication

Uses the existing API token system (`cf_` prefix, SHA-256 hashed, stored in `api_tokens` table).

- The API token is passed as a `Bearer` token in the HTTP `Authorization` header on MCP requests
- On each request, the token is validated and resolved to a user + role
- RBAC is enforced on every tool call based on the resolved user's role
- If the token is invalid or missing, the MCP server rejects the connection

### Self-Approval Guard

When `approve_certificate` or `deny_certificate` is called, the backend checks if `requested_by` on the certificate matches the authenticated user's ID. If they match, the operation is rejected with an error message. This prevents an agent from approving its own certificate requests.

This guard is enforced in the service layer, so it applies to MCP, REST API, and any future interface.

## Tools

### Read Tools

#### `list_cas`
List all certificate authorities.

**Parameters:**
- `status` (optional, string): Filter by status — `active`, `disabled`

**Returns:** List of CAs with id, name, type, status, subject_dn, not_before, not_after, algorithm.

#### `get_ca`
Get detailed information about a specific CA.

**Parameters:**
- `ca_id` (optional, string): CA ID
- `name` (optional, string): CA name (alternative lookup)

One of `ca_id` or `name` must be provided.

**Returns:** Full CA details including subject_dn, serial, validity dates, algorithm, key size, auto_approve, status.

#### `get_ca_chain`
Get the full certificate chain for a CA.

**Parameters:**
- `ca_id` (string, required): CA ID

**Returns:** List of PEM-encoded certificates from the CA up to the root.

#### `list_certificates`
Search and list certificates with filtering and sorting.

**Parameters:**
- `ca_id` (optional, string): Filter by issuing CA
- `status` (optional, string): Filter by status — `active`, `pending`, `revoked`, `expired`
- `search` (optional, string): Search by subject DN
- `sort_by` (optional, string): Sort field — `subject_dn`, `type`, `status`, `not_after`, `created_at` (default: `created_at`)
- `sort_order` (optional, string): `asc` or `desc` (default: `desc`)
- `page` (optional, int): Page number (default: 1)
- `per_page` (optional, int): Results per page (default: 25, max: 100)

**Returns:** Paginated list of certificates with id, subject_dn, type, status, serial, san, not_before, not_after, key_algorithm.

#### `get_certificate`
Get detailed information about a specific certificate.

**Parameters:**
- `cert_id` (string, required): Certificate ID

**Returns:** Full certificate details including subject_dn, serial, type, status, san, validity dates, algorithm, key_usage, extended_key_usage, revocation info, has_private_key.

#### `get_crl_info`
Get CRL status for a CA.

**Parameters:**
- `ca_id` (string, required): CA ID

**Returns:** CRL number, this_update, next_update, revoked certificate count.

### Issue Tools

#### `create_certificate`
Create and issue a new certificate.

**Parameters:**
- `ca_id` (string, required): Issuing CA ID
- `common_name` (string, required): Certificate CN
- `organization` (optional, string): Organization (O)
- `org_unit` (optional, string): Organizational Unit (OU)
- `country` (optional, string): Country code (C), max 2 chars
- `state` (optional, string): State/Province (ST)
- `locality` (optional, string): Locality (L)
- `san` (optional, list of objects): Subject Alternative Names, each with `type` (DNS, IP, Email, URI) and `value`
- `type` (optional, string): Certificate type — `server`, `client`, `custom` (default: `server`)
- `key_algorithm` (optional, string): `RSA` or `EC` (default: `RSA`)
- `key_size` (optional, int): Key size in bits (default: 2048)
- `validity_days` (optional, int): Validity period in days
- `key_usage` (optional, list of strings): Key usage extensions
- `extended_key_usage` (optional, list of strings): Extended key usage extensions

**Returns:** Created certificate details. If the CA has auto-approve enabled, the certificate will be active immediately with `certificate_pem` populated. Otherwise, status will be `pending`.

#### `submit_csr`
Submit a Certificate Signing Request for signing.

**Parameters:**
- `ca_id` (string, required): Issuing CA ID
- `csr_pem` (string, required): PEM-encoded CSR
- `type` (optional, string): Certificate type — `server`, `client`, `custom` (default: `server`)
- `validity_days` (optional, int): Validity period in days

**Returns:** Created certificate details (pending or active depending on auto-approve).

#### `approve_certificate`
Approve a pending certificate request.

**Parameters:**
- `cert_id` (string, required): Certificate ID

**Returns:** Updated certificate details with status `active`.

**Guard:** Rejects if the authenticated user is the same as the certificate requester.

#### `deny_certificate`
Deny a pending certificate request.

**Parameters:**
- `cert_id` (string, required): Certificate ID

**Returns:** Updated certificate details with status `denied`.

**Guard:** Rejects if the authenticated user is the same as the certificate requester.

#### `download_certificate`
Download a certificate or its private key.

**Parameters:**
- `cert_id` (string, required): Certificate ID
- `format` (optional, string): Output format — `pem`, `der`, `pkcs12` (default: `pem`)
- `key_only` (optional, bool): Download only the private key (default: false)
- `passphrase` (optional, string): Passphrase for PKCS12 export

**Returns:** Certificate or key data as a string (PEM) or base64-encoded (DER/PKCS12).

## Implementation Details

### Dependencies

- `mcp[http]` — MCP Python SDK with HTTP transport support
- No other new dependencies required

### File Structure

```
backend/app/
  mcp_server.py          — MCP server setup, tool definitions, auth middleware
```

Single file. The MCP server imports and calls the existing service classes. Tool functions are thin wrappers that:

1. Parse tool parameters
2. Create a database session
3. Call the appropriate service method
4. Format and return the result

### Mounting

In `backend/app/main.py`, the MCP ASGI app is mounted at `/mcp`:

```python
from app.mcp_server import mcp_app
app.mount("/mcp", mcp_app)
```

### Error Handling

Tool errors return structured MCP error responses with clear messages:
- Invalid/missing token: authentication error
- Insufficient role: authorization error
- Resource not found: "CA not found" / "Certificate not found"
- Validation errors: parameter-specific messages
- Self-approval blocked: "Cannot approve a certificate you requested"

### RBAC Mapping

The API token's associated user role determines access:

| Role | Read tools | create/submit | approve/deny | download |
|------|-----------|---------------|-------------|----------|
| admin | Yes | Yes | Yes | Yes |
| operator | Yes | Yes | Yes | Yes |
| requester | Own certs only | Yes | No | Own certs only |
| auditor | Yes | No | No | No |

## Testing

- Unit tests for each tool function with mocked services
- Integration test verifying token auth flow
- Test self-approval guard on approve/deny
- Test RBAC enforcement per role
