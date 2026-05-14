# Import CAs and Certificates — Design Spec

## Overview

Add the ability to import existing Certificate Authorities and certificates into the PKI Manager from PEM, DER, and PKCS12/PFX files. Import buttons appear inline on the CA list and Certificate list pages.

## Backend

### Endpoint: `POST /api/v1/cas/import`

Accepts multipart form data:

- `cert_file` (required) — certificate file (PEM or DER)
- `key_file` (required) — private key file (PEM or DER). Required because the CA must be able to sign.
- `pkcs12_file` (alternative) — PKCS12/PFX file containing cert + key. Used instead of cert_file + key_file.
- `passphrase` (optional) — passphrase for PKCS12 or encrypted private key
- `name` (required) — display name for the CA

**Processing:**

1. Detect format (PEM vs DER vs PKCS12) by inspecting file content (PEM starts with `-----BEGIN`, PKCS12 is binary)
2. Parse the certificate — extract subject DN, serial, validity dates, basic constraints, key algorithm/size
3. Validate that the certificate has `CA:TRUE` in basic constraints
4. Validate the private key matches the certificate's public key
5. Auto-detect parent: query all existing CAs, compare the imported cert's issuer field against each CA's subject. If a match is found, set `parent_ca_id`. If no match, import as root CA.
6. Encrypt the private key with the master key
7. Store in `certificate_authorities` table with `type` set based on whether a parent was found (root vs intermediate)
8. Return the created CA record with `parent_detected: true/false` in the response

**Access:** admin, operator

### Endpoint: `POST /api/v1/certificates/import`

Accepts multipart form data:

- `cert_file` (required) — certificate file (PEM or DER)
- `key_file` (optional) — private key file (PEM or DER)
- `pkcs12_file` (alternative) — PKCS12/PFX file containing cert + key
- `passphrase` (optional) — passphrase for PKCS12 or encrypted private key
- `ca_id` (optional) — manually specify issuing CA if auto-detect fails

**Processing:**

1. Detect format and parse the certificate — extract all fields (subject, serial, SANs, validity, key usage, EKU)
2. Private key (if provided): validate it matches the cert's public key, encrypt with master key
3. Auto-detect issuing CA: compare cert's issuer against existing CAs' subjects. If found, set `ca_id`. If not and `ca_id` not provided, reject with error asking user to select a CA.
4. Set certificate status to `active` (it's already issued)
5. Store in `certificates` table
6. Return the created certificate record

**Access:** admin, operator, requester

### Crypto Service Additions

Add to `crypto_service.py`:

- `parse_certificate(cert_pem: str) -> dict` — extract all fields from a PEM certificate
- `load_pkcs12(data: bytes, passphrase: str | None) -> tuple[str, str, list[str]]` — returns (cert_pem, key_pem, chain_pems)
- `der_to_pem_cert(der_bytes: bytes) -> str` — convert DER certificate to PEM
- `der_to_pem_key(der_bytes: bytes) -> str` — convert DER private key to PEM
- `verify_key_matches_cert(key_pem: str, cert_pem: str) -> bool` — confirm private key matches certificate

## Frontend

### CA List Page — Import Button

Add "Import CA" button next to "Create Root CA" button. Opens a modal:

**Import CA Modal:**
- Format selector: PEM (default), PKCS12/PFX
- If PEM:
  - Certificate file upload (accepts .pem, .crt, .cer, .der)
  - Private key file upload (accepts .pem, .key, .der)
- If PKCS12:
  - PKCS12 file upload (accepts .p12, .pfx)
  - Passphrase input
- CA Name text input (required)
- "Parse" button → calls backend, displays parsed cert details (subject, issuer, validity, auto-detected parent)
- User reviews and confirms → "Import" button saves

### Certificate List Page — Import Button

Add "Import" button next to "New Certificate" / "Submit CSR" buttons. Opens a modal:

**Import Certificate Modal:**
- Format selector: PEM (default), PKCS12/PFX
- If PEM:
  - Certificate file upload (required)
  - Private key file upload (optional)
- If PKCS12:
  - PKCS12 file upload
  - Passphrase input
- CA selector dropdown (pre-filled if auto-detected, required)
- "Parse" button → displays parsed cert details
- User reviews and confirms → "Import" button saves

### Routes

No new routes — both flows use modals on existing pages.

## Audit

- New audit action: `imported_ca` and `imported_cert`
- Logged with details including source format and whether parent was auto-detected
