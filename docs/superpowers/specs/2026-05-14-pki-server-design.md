# PKI Certificate Management Server — Design Spec

## Overview

A web-based PKI certificate management platform for creating and managing Certificate Authorities, issuing certificates, and handling the full certificate lifecycle. Supports internal/corporate use, lab environments, and multi-tenant scenarios.

**Stack:** React frontend, FastAPI backend, SQLite (swappable to PostgreSQL), Python `cryptography` library for all certificate operations.

## Architecture

### Approach: FastAPI with Background Tasks

Synchronous request handling for certificate operations (key generation, signing, format conversion — all fast). Background tasks via APScheduler for scheduled work: CRL regeneration, expiration checks, audit log maintenance.

### Key Principles

- **Frontend is presentation only.** No business logic, no crypto, no certificate parsing. The React app calls the REST API and renders responses.
- **`crypto_service.py` is the single point of contact with the `cryptography` library.** All other services go through it. No other file performs certificate operations directly.
- **SQLAlchemy with configurable connection string.** Default: SQLite (`sqlite:///./pki.db`). Swap to PostgreSQL by changing one environment variable (`DATABASE_URL`).
- **Alembic for migrations** so schema changes work across both database backends.
- **API-first design.** The REST API is a first-class product, not just a backend for the UI. Scripts, CI pipelines, and external tools can consume it directly.

### Project Structure

```
pki_server/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings (DB URL, master key, etc.)
│   │   ├── database.py              # SQLAlchemy engine/session setup
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── routers/                 # FastAPI route handlers
│   │   ├── services/                # Business logic layer
│   │   │   ├── crypto_service.py    # All cryptography library operations
│   │   │   ├── ca_service.py        # CA management logic
│   │   │   ├── certificate_service.py
│   │   │   ├── crl_service.py
│   │   │   ├── ocsp_service.py
│   │   │   └── auth_service.py
│   │   ├── utils/                   # Encryption helpers, validators
│   │   └── scheduler/               # APScheduler jobs
│   ├── alembic/                     # DB migrations
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
```

## Data Model

### users

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| username | String | Unique |
| email | String | Unique |
| password_hash | String | bcrypt via passlib |
| role | Enum | admin, operator, requester, auditor |
| is_active | Boolean | Soft disable |
| created_at | DateTime | |
| updated_at | DateTime | |

### certificate_authorities

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| name | String | Display name |
| description | Text | Optional |
| type | Enum | root, intermediate |
| status | Enum | active, disabled, expired, revoked |
| parent_ca_id | UUID FK → self | Null for root CAs. Enables flexible hierarchy of any depth. |
| private_key_encrypted | Text | PEM, encrypted with master key (AES-256-GCM) |
| certificate_pem | Text | |
| key_algorithm | Enum | RSA, EC |
| key_size | Integer | e.g., 2048, 4096, 256, 384 |
| subject_dn | String | Full distinguished name |
| serial_number | String | Hex string |
| not_before | DateTime | |
| not_after | DateTime | |
| max_path_length | Integer | Nullable, for path length constraint |
| auto_approve | Boolean | Controls per-CA approval workflow |
| crl_regen_interval_hours | Integer | Default: 24. Used by scheduler to regenerate CRLs. |
| ocsp_signing_mode | Enum | ca_key, dedicated_cert — controls whether OCSP responses are signed by the CA key or a dedicated OCSP signing cert |
| ocsp_signing_cert_pem | Text | Nullable, populated when ocsp_signing_mode is dedicated_cert |
| ocsp_signing_key_encrypted | Text | Nullable, encrypted private key for dedicated OCSP signing cert |
| crl_distribution_url | String | Optional |
| ocsp_url | String | Optional |
| created_by | UUID FK → users | |
| created_at | DateTime | |
| updated_at | DateTime | |

### certificates

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| ca_id | UUID FK → certificate_authorities | Issuing CA |
| status | Enum | pending, active, revoked, expired, denied |
| type | Enum | server, client, custom |
| private_key_encrypted | Text | Nullable — null when submitted as CSR |
| certificate_pem | Text | Nullable while pending |
| csr_pem | Text | Nullable |
| key_algorithm | Enum | RSA, EC |
| key_size | Integer | |
| subject_dn | String | |
| serial_number | String | Hex string |
| san | JSON | List of {type, value} objects. Types: DNS, IP, Email, URI |
| not_before | DateTime | |
| not_after | DateTime | |
| key_usage | JSON | List of key usage flags (e.g., digital_signature, key_encipherment) |
| extended_key_usage | JSON | List of EKU OIDs (e.g., server_auth, client_auth) |
| custom_extensions | JSON | List of {oid, critical, value} objects for advanced mode |
| revocation_date | DateTime | Nullable |
| revocation_reason | Enum | Nullable: key_compromise, ca_compromise, affiliation_changed, superseded, cessation_of_operation, certificate_hold, unspecified |
| requested_by | UUID FK → users | |
| approved_by | UUID FK → users | Nullable |
| created_at | DateTime | |
| updated_at | DateTime | |

### certificate_revocation_lists

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| ca_id | UUID FK → certificate_authorities | |
| crl_pem | Text | |
| this_update | DateTime | |
| next_update | DateTime | |
| crl_number | Integer | Incrementing per CA |
| created_at | DateTime | |

### audit_logs

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| user_id | UUID FK → users | |
| action | Enum | created_ca, issued_cert, revoked_cert, approved_request, denied_request, login, logout, config_change, downloaded_cert, created_user, updated_user, generated_crl, renewed_cert, submitted_csr |
| resource_type | Enum | ca, certificate, user, crl |
| resource_id | UUID | |
| details | JSON | Full context of the action |
| ip_address | String | |
| created_at | DateTime | |

### Design Decisions

- **`parent_ca_id` self-referential FK** enables flexible CA hierarchy of any depth. Any CA can issue end-entity certs or sign subordinate CAs regardless of its position in the chain.
- **`auto_approve` on the CA** — each CA independently controls whether certificate requests need operator approval or are issued immediately.
- **`ocsp_signing_mode` on the CA** — configurable per CA whether OCSP responses are signed by the CA key itself or a dedicated OCSP signing certificate.
- **`private_key_encrypted`** on both CAs and certs — encrypted at rest using a master key from config. Null on certificates when the user submits a CSR (they keep their own key).
- **`custom_extensions` JSON** — the advanced mode escape hatch for arbitrary X.509 extensions.
- **Serial numbers** managed by the app (incrementing per CA), not by the cryptography library.
- **JSON columns** (san, key_usage, extended_key_usage, custom_extensions) are a database storage detail. The frontend presents these as structured form elements (repeatable field groups, checkboxes, key/value inputs), never raw JSON.

## API Design

All endpoints versioned under `/api/v1`. JWT Bearer token auth on all routes except login and OCSP.

### Auth — `/api/v1/auth`

- `POST /login` — returns JWT access + refresh tokens
- `POST /logout` — invalidate token
- `GET /me` — current user profile
- `PUT /me/password` — change own password

### Users — `/api/v1/users` (admin only)

- `GET /` — list users (filtering, pagination)
- `POST /` — create user
- `GET /{id}` — get user details
- `PUT /{id}` — update user (role, active status)
- `DELETE /{id}` — deactivate user (soft delete)

### Certificate Authorities — `/api/v1/cas`

- `GET /` — list all CAs (flat list)
- `GET /tree` — full CA hierarchy as nested tree
- `POST /` — create root CA
- `GET /{id}` — CA details (includes chain info)
- `PUT /{id}` — update CA settings (auto_approve, description, ocsp_signing_mode, etc.)
- `POST /{id}/intermediate` — create intermediate CA signed by this CA
- `GET /{id}/chain` — download full certificate chain
- `POST /{id}/disable` / `POST /{id}/enable` — toggle CA status

### Certificates — `/api/v1/certificates`

- `GET /` — list certificates (filterable by CA, status, expiry range)
- `POST /` — request new certificate (backend generates key + cert)
- `POST /csr` — submit CSR for signing
- `GET /{id}` — certificate details
- `POST /{id}/approve` — approve pending request (operator/admin)
- `POST /{id}/deny` — deny pending request
- `POST /{id}/revoke` — revoke certificate
- `POST /{id}/renew` — renew with same details, new validity
- `GET /{id}/download` — download in specified format (query param: `format=pem|der|pkcs12`, optional `passphrase` for PKCS12)

### CRL & OCSP — `/api/v1`

- `GET /cas/{id}/crl` — download current CRL for a CA
- `POST /cas/{id}/crl/generate` — force CRL regeneration
- `GET /ocsp/{ca_id}` — OCSP responder (RFC 6960, HTTP GET and POST)
- `POST /ocsp/{ca_id}` — OCSP responder (POST method)

### Audit — `/api/v1/audit`

- `GET /logs` — search/filter audit logs (by user, action, resource, date range)
- `GET /logs/export` — export as CSV

### Dashboard — `/api/v1/dashboard`

- `GET /stats` — summary counts (active CAs, certs, pending requests, expiring soon)
- `GET /expiring` — certs expiring within configurable window

### Access Control

| Role | Permissions |
|------|------------|
| admin | Full access to everything |
| operator | Manage CAs, approve/deny requests, issue/revoke certs, view audit logs |
| requester | Create certificate requests, view own certificates |
| auditor | Read-only access to everything including audit logs |

Enforced via FastAPI dependencies. Pagination on all list endpoints (`?page=1&per_page=25`). Consistent error responses with status codes and detail messages.

## Crypto Service Layer

`crypto_service.py` uses the Python `cryptography` library for all certificate operations. No subprocess calls, no temp files — keys and certs exist as in-memory objects.

### Methods

- `generate_key(algorithm, key_size) → PEM string`
- `create_root_ca(key_pem, subject, validity_days, extensions) → cert PEM`
- `create_intermediate_ca(key_pem, subject, ca_cert, ca_key, validity_days, extensions) → cert PEM`
- `sign_csr(csr_pem, ca_cert, ca_key, validity_days, extensions) → cert PEM`
- `generate_csr(key_pem, subject, sans) → CSR PEM`
- `generate_crl(ca_cert, ca_key, revoked_certs, next_update_days) → CRL PEM`
- `build_ocsp_response(ca_cert, signing_key, cert_status, ...) → OCSP response bytes`
- `convert_format(cert_pem, key_pem, format, passphrase) → bytes` (PEM/DER/PKCS12)
- `generate_ocsp_signing_cert(ca_cert, ca_key) → (cert PEM, key PEM)`

### Security

- **Master key** — loaded from environment variable (`PKI_MASTER_KEY`), never stored in database. Used for AES-256-GCM encryption/decryption of private keys before storage.
- **No temp files** — all crypto operations happen in memory. Private keys are never written to disk.
- **Input validation** — Pydantic schemas validate all inputs before they reach the crypto layer. DN components restricted to safe characters.
- **JWT auth** — short-lived access tokens, refresh token rotation. Tokens include user ID and role.
- **Password hashing** — bcrypt via passlib.
- **Rate limiting** — on auth endpoints to prevent brute force.

## Background Scheduler

APScheduler runs within the FastAPI process:

- **CRL regeneration** — configurable interval per CA (default: 24 hours). Regenerates and stores the CRL.
- **Expiration checks** — daily scan, flags certificates expiring within a configurable window (default: 30 days). Surfaces in the dashboard only (no email/webhook notifications in initial build).
- **Audit log maintenance** — optional, archive or prune logs older than a configurable retention period.

## Frontend

### Stack

React with React Router. Presentation only — all logic on the backend.

### Theme

Obsidian-inspired design with light and dark mode, toggled via sun/moon icon in the top navbar, persisted to localStorage.

- **Monochrome SVG icons** — stroke-style, single color matching text weight. No filled or colored icons.
- **Color used only for status** — green (active/healthy), amber (warning/pending), red (error/expiring). Everything else is grayscale.
- **Dark palette:** #161616, #181818, #1e1e1e, #252525. Text: #e0e0e0, #aaa, #666.
- **Light palette:** #fff, #fafafa, #f0f0f0. Text: #222, #555, #999.
- **Minimal borders** — subtle 1px separators. Cards use background contrast, not heavy borders.

### Layout

- **Top navbar** — app branding (left), theme toggle + notifications bell + user avatar/name/role with dropdown (Profile, Settings, Logout) on the right.
- **Left sidebar** — main navigation grouped into sections (Main: Dashboard, Certificate Authorities, Certificates, Pending Requests. Management: Audit Log, Users). Active page indicator via left border highlight. Badge counts on actionable items (Pending Requests). Collapsible on smaller screens.
- **Main content area** — right of sidebar, full remaining width.

### Key Pages

1. **Dashboard** — stat cards (Active CAs, Active Certs, Pending, Expiring Soon), expiring certificates list, recent activity feed.
2. **Certificate Authorities** — list/table view + tree hierarchy view toggle. Create Root CA and Create Intermediate CA actions.
3. **CA Detail** — CA info, chain of trust, issued certificates list, subordinate CAs, settings (auto_approve, OCSP signing mode), actions (disable/enable).
4. **Certificates** — filterable table (by CA, status, expiry). Bulk actions where applicable.
5. **Certificate Detail** — all cert fields, chain of trust visualization, status badge, download buttons (PEM/DER/PKCS12), action buttons (revoke/renew) based on status and user role.
6. **Pending Requests** — queue of pending certificate requests with approve/deny actions. Shows CSR details for review.
7. **Create Certificate** — form with guided mode (CN, SANs as repeatable fields, type dropdown, validity) and advanced toggle (key usage checkboxes, EKU checkboxes, custom extensions as repeatable OID/value pairs).
8. **Submit CSR** — upload/paste CSR PEM, select issuing CA, review parsed CSR details, submit.
9. **Audit Log** — searchable/filterable table with date range picker, action type filter, user filter. CSV export.
10. **Users** — user management table (admin only). Create/edit user with role assignment.

### Form Design for JSON-Backed Fields

These database JSON columns are presented as structured UI elements:

- **SANs** — repeatable field group: dropdown (DNS/IP/Email/URI) + text input. Add/remove buttons.
- **Key Usage** — checkboxes: Digital Signature, Key Encipherment, Data Encipherment, Key Agreement, Certificate Sign, CRL Sign, etc.
- **Extended Key Usage** — checkboxes: TLS Web Server Auth, TLS Web Client Auth, Code Signing, Email Protection, OCSP Signing, etc.
- **Custom Extensions** — repeatable group: OID text input + critical checkbox + value text input. Advanced mode only.

## OCSP Responder

Built into the FastAPI backend as a standard endpoint at `/api/v1/ocsp/{ca_id}`.

- Accepts standard OCSP requests via HTTP GET and POST per RFC 6960.
- Queries the database for certificate revocation status.
- Builds and signs OCSP responses using the `cryptography` library's `x509.ocsp` module.
- **Signing mode configurable per CA:**
  - **CA key** (default) — OCSP responses signed directly by the CA's private key. Simpler setup.
  - **Dedicated OCSP signing cert** — auto-generated OCSP signing certificate issued by the CA when this mode is selected. Better practice for production as it avoids using the CA key for every OCSP query.
- OCSP URL in issued certificates points back to this endpoint.

## Deployment (Future)

Docker Compose stack with separate containers for frontend, backend, and PostgreSQL. Not in scope for initial build — focus is on working code with SQLite.
