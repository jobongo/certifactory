# MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an MCP server to Certifactory so AI agents can list CAs, search certificates, issue certs, submit CSRs, approve/deny (with self-approval guard), and download certificates — all authenticated via existing API tokens.

**Architecture:** The MCP server is embedded in the FastAPI backend as a Streamable HTTP endpoint mounted at `/mcp`. It uses the MCP Python SDK (`mcp[http]`) and calls the existing service layer directly, sharing database sessions. Auth is via `cf_` API tokens in the Bearer header.

**Tech Stack:** Python MCP SDK (`mcp[http]`), FastAPI mount, existing SQLAlchemy services

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/requirements.txt` | Modify | Add `mcp[http]` dependency |
| `backend/app/mcp_server.py` | Create | MCP server setup, auth, all 11 tool definitions |
| `backend/app/services/certificate_service.py` | Modify | Add self-approval guard to `approve()` and `deny()` |
| `backend/app/main.py` | Modify | Mount MCP ASGI app at `/mcp` |
| `backend/tests/test_mcp.py` | Create | Tests for MCP tools, auth, and self-approval guard |

---

### Task 1: Add Self-Approval Guard to Certificate Service

**Files:**
- Modify: `backend/app/services/certificate_service.py:165-205`
- Test: `backend/tests/test_certificates.py` (existing, add test)

- [ ] **Step 1: Write the failing test for self-approval guard**

Add to `backend/tests/test_certificates.py`:

```python
def test_approve_self_request_blocked(client, admin_headers, admin_user):
    ca_data = {
        "name": "Test CA", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": False,
        "subject": {"CN": "Test CA"}
    }
    ca = client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()

    cert_data = {
        "ca_id": ca["id"], "subject": {"CN": "self-approve-test"},
        "type": "server", "key_algorithm": "RSA", "key_size": 2048, "validity_days": 90
    }
    cert = client.post("/api/v1/certificates", json=cert_data, headers=admin_headers).json()
    assert cert["status"] == "pending"

    resp = client.post(f"/api/v1/certificates/{cert['id']}/approve", headers=admin_headers)
    assert resp.status_code == 400
    assert "cannot approve" in resp.json()["detail"].lower()


def test_deny_self_request_blocked(client, admin_headers, admin_user):
    ca_data = {
        "name": "Test CA 2", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": False,
        "subject": {"CN": "Test CA 2"}
    }
    ca = client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()

    cert_data = {
        "ca_id": ca["id"], "subject": {"CN": "self-deny-test"},
        "type": "server", "key_algorithm": "RSA", "key_size": 2048, "validity_days": 90
    }
    cert = client.post("/api/v1/certificates", json=cert_data, headers=admin_headers).json()

    resp = client.post(f"/api/v1/certificates/{cert['id']}/deny", headers=admin_headers)
    assert resp.status_code == 400
    assert "cannot deny" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_certificates.py::test_approve_self_request_blocked tests/test_certificates.py::test_deny_self_request_blocked -v`

Expected: FAIL — approval and denial currently succeed without the guard.

- [ ] **Step 3: Add self-approval guard to the service layer**

In `backend/app/services/certificate_service.py`, modify the `approve` method. Add after the `if cert.status != CertificateStatus.pending:` check:

```python
    def approve(self, db: Session, user_id: str, cert_id: str) -> Certificate:
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if cert.status != CertificateStatus.pending:
            raise ValueError("Certificate is not pending")
        if cert.requested_by == user_id:
            raise ValueError("Cannot approve a certificate you requested")
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == cert.ca_id).first()
```

Similarly, modify the `deny` method. Add after the pending check:

```python
    def deny(self, db: Session, user_id: str, cert_id: str) -> Certificate:
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if cert.status != CertificateStatus.pending:
            raise ValueError("Certificate is not pending")
        if cert.requested_by == user_id:
            raise ValueError("Cannot deny a certificate you requested")
        cert.status = CertificateStatus.denied
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_certificates.py::test_approve_self_request_blocked tests/test_certificates.py::test_deny_self_request_blocked -v`

Expected: PASS

- [ ] **Step 5: Run the full certificate test suite to check for regressions**

Run: `cd backend && .venv/bin/python -m pytest tests/test_certificates.py -v`

Expected: All tests pass. Existing approve/deny tests may fail if they use the same user for request and approval — if so, create a second user fixture for those tests.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/certificate_service.py backend/tests/test_certificates.py
git commit -m "feat: add self-approval guard to certificate approve/deny"
```

---

### Task 2: Install MCP SDK Dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the MCP SDK to requirements**

Add to `backend/requirements.txt`:

```
mcp[http]>=1.9.0
```

- [ ] **Step 2: Install the dependency**

Run: `cd backend && .venv/bin/pip install "mcp[http]>=1.9.0"`

Expected: Successful installation with no conflicts.

- [ ] **Step 3: Verify import works**

Run: `cd backend && .venv/bin/python -c "from mcp.server.fastmcp import FastMCP; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add mcp[http] dependency"
```

---

### Task 3: Create MCP Server with Auth and Read Tools

**Files:**
- Create: `backend/app/mcp_server.py`
- Create: `backend/tests/test_mcp.py`

- [ ] **Step 1: Write tests for auth and read tools**

Create `backend/tests/test_mcp.py`:

```python
import pytest
from unittest.mock import patch
from app.mcp_server import resolve_user
from app.database import SessionLocal
from app.models import User, UserRole
from app.models.api_token import ApiToken
from app.services.auth_service import AuthService


@pytest.fixture
def mcp_user(db):
    auth = AuthService()
    user = User(
        username="mcp_agent", email="agent@test.com",
        password_hash=auth.hash_password("agent123"), role=UserRole.operator,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def mcp_token(db, mcp_user):
    raw = ApiToken.generate_token()
    token = ApiToken(user_id=mcp_user.id, name="mcp-test", token_hash=ApiToken.hash_token(raw), token_prefix=raw[:10])
    db.add(token)
    db.commit()
    return raw


def test_resolve_user_valid_token(db, mcp_user, mcp_token):
    user = resolve_user(mcp_token, db)
    assert user.id == mcp_user.id
    assert user.role == UserRole.operator


def test_resolve_user_invalid_token(db):
    with pytest.raises(ValueError, match="Invalid or revoked API token"):
        resolve_user("cf_invalidtoken", db)


def test_resolve_user_missing_prefix(db):
    with pytest.raises(ValueError, match="API token required"):
        resolve_user("not_a_cf_token", db)


def test_resolve_user_none(db):
    with pytest.raises(ValueError, match="API token required"):
        resolve_user(None, db)
```

- [ ] **Step 2: Create the MCP server file with auth and read tools**

Create `backend/app/mcp_server.py`:

```python
import base64
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CAStatus, Certificate, CertificateAuthority, CertificateStatus, User, UserRole
from app.models.api_token import ApiToken
from app.services.ca_service import CAService
from app.services.certificate_service import CertificateService
from app.services.crl_service import CRLService

ca_service = CAService()
cert_service = CertificateService()
crl_service = CRLService()


def resolve_user(token: str | None, db: Session) -> User:
    if not token or not token.startswith("cf_"):
        raise ValueError("API token required (must start with cf_)")
    token_hash = ApiToken.hash_token(token)
    api_token = db.query(ApiToken).filter(ApiToken.token_hash == token_hash, ApiToken.is_active == True).first()
    if not api_token:
        raise ValueError("Invalid or revoked API token")
    user = db.query(User).filter(User.id == api_token.user_id).first()
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")
    api_token.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return user


def _check_role(user: User, *allowed: UserRole):
    if user.role not in allowed:
        raise ValueError(f"Insufficient permissions. Required: {', '.join(r.value for r in allowed)}")


def _ca_to_dict(ca: CertificateAuthority) -> dict:
    return {
        "id": ca.id, "name": ca.name, "type": ca.type.value, "status": ca.status.value,
        "subject_dn": ca.subject_dn, "serial_number": ca.serial_number,
        "key_algorithm": ca.key_algorithm.value, "key_size": ca.key_size,
        "not_before": ca.not_before.isoformat() if ca.not_before else None,
        "not_after": ca.not_after.isoformat() if ca.not_after else None,
        "auto_approve": ca.auto_approve,
        "description": ca.description,
    }


def _cert_to_dict(cert: Certificate) -> dict:
    return {
        "id": cert.id, "ca_id": cert.ca_id, "status": cert.status.value,
        "type": cert.type.value, "subject_dn": cert.subject_dn,
        "serial_number": cert.serial_number, "san": cert.san,
        "key_algorithm": cert.key_algorithm.value, "key_size": cert.key_size,
        "not_before": cert.not_before.isoformat() if cert.not_before else None,
        "not_after": cert.not_after.isoformat() if cert.not_after else None,
        "key_usage": cert.key_usage, "extended_key_usage": cert.extended_key_usage,
        "has_private_key": cert.has_private_key,
        "revocation_date": cert.revocation_date.isoformat() if cert.revocation_date else None,
        "revocation_reason": cert.revocation_reason.value if cert.revocation_reason else None,
        "requested_by": cert.requested_by,
        "approved_by": cert.approved_by,
    }


mcp = FastMCP("Certifactory", instructions="PKI certificate management. Authenticate with a cf_ API token.")


@mcp.tool()
def list_cas(token: str, status: str | None = None) -> str:
    """List all certificate authorities. Optionally filter by status (active, disabled)."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor)
        query = db.query(CertificateAuthority)
        if status:
            query = query.filter(CertificateAuthority.status == CAStatus(status))
        cas = query.all()
        return str([_ca_to_dict(ca) for ca in cas])
    finally:
        db.close()


@mcp.tool()
def get_ca(token: str, ca_id: str | None = None, name: str | None = None) -> str:
    """Get detailed information about a CA by ID or name. Provide one of ca_id or name."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor)
        if ca_id:
            ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
        elif name:
            ca = db.query(CertificateAuthority).filter(CertificateAuthority.name == name).first()
        else:
            raise ValueError("Provide either ca_id or name")
        if not ca:
            raise ValueError("CA not found")
        return str(_ca_to_dict(ca))
    finally:
        db.close()


@mcp.tool()
def get_ca_chain(token: str, ca_id: str) -> str:
    """Get the full PEM certificate chain for a CA, from the CA up to the root."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor)
        chain = ca_service.get_chain(db, ca_id)
        if not chain:
            raise ValueError("CA not found")
        return "\n".join(chain)
    finally:
        db.close()


@mcp.tool()
def list_certificates(
    token: str, ca_id: str | None = None, status: str | None = None,
    search: str | None = None, sort_by: str = "created_at",
    sort_order: str = "desc", page: int = 1, per_page: int = 25,
) -> str:
    """Search and list certificates. Filter by ca_id, status (active/pending/revoked/expired), or search by subject DN."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor, UserRole.requester)
        query = db.query(Certificate)
        if user.role == UserRole.requester:
            query = query.filter(Certificate.requested_by == user.id)
        if ca_id:
            query = query.filter(Certificate.ca_id == ca_id)
        if status:
            query = query.filter(Certificate.status == CertificateStatus(status))
        if search:
            query = query.filter(Certificate.subject_dn.ilike(f"%{search}%"))
        total = query.count()
        sort_col = getattr(Certificate, sort_by, Certificate.created_at)
        order = sort_col.asc() if sort_order == "asc" else sort_col.desc()
        items = query.order_by(order).offset((page - 1) * per_page).limit(per_page).all()
        return str({"total": total, "page": page, "items": [_cert_to_dict(c) for c in items]})
    finally:
        db.close()


@mcp.tool()
def get_certificate(token: str, cert_id: str) -> str:
    """Get detailed information about a specific certificate by ID."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor, UserRole.requester)
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if user.role == UserRole.requester and cert.requested_by != user.id:
            raise ValueError("Certificate not found")
        return str(_cert_to_dict(cert))
    finally:
        db.close()


@mcp.tool()
def get_crl_info(token: str, ca_id: str) -> str:
    """Get CRL (Certificate Revocation List) status for a CA."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator)
        crl = crl_service.get_latest_crl(db, ca_id)
        if not crl:
            return "No CRL generated yet for this CA"
        return str({
            "crl_number": crl.crl_number,
            "this_update": crl.this_update.isoformat(),
            "next_update": crl.next_update.isoformat(),
        })
    finally:
        db.close()
```

- [ ] **Step 3: Run auth tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py -v`

Expected: All 4 auth tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/mcp_server.py backend/tests/test_mcp.py
git commit -m "feat: add MCP server with auth and read tools"
```

---

### Task 4: Add Issue Tools (create, submit CSR, approve, deny, download)

**Files:**
- Modify: `backend/app/mcp_server.py`
- Modify: `backend/tests/test_mcp.py`

- [ ] **Step 1: Write tests for issue tools**

Add to `backend/tests/test_mcp.py`:

```python
from app.mcp_server import create_certificate, list_cas, approve_certificate, deny_certificate


@pytest.fixture
def test_ca(client, admin_headers):
    ca_data = {
        "name": "MCP Test CA", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": True,
        "subject": {"CN": "MCP Test CA"}
    }
    return client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()


@pytest.fixture
def manual_ca(client, admin_headers):
    ca_data = {
        "name": "Manual CA", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": False,
        "subject": {"CN": "Manual CA"}
    }
    return client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()


def test_create_certificate_auto_approve(db, mcp_user, mcp_token, test_ca):
    result = create_certificate(
        token=mcp_token, ca_id=test_ca["id"], common_name="agent.example.com",
        type="server", key_algorithm="RSA", key_size=2048, validity_days=90,
    )
    assert "active" in result
    assert "agent.example.com" in result


def test_create_certificate_pending(db, mcp_user, mcp_token, manual_ca):
    result = create_certificate(
        token=mcp_token, ca_id=manual_ca["id"], common_name="pending.example.com",
    )
    assert "pending" in result


def test_approve_self_blocked_via_mcp(db, mcp_user, mcp_token, manual_ca):
    result = create_certificate(
        token=mcp_token, ca_id=manual_ca["id"], common_name="self-block.example.com",
    )
    import ast
    cert_dict = ast.literal_eval(result)
    with pytest.raises(ValueError, match="Cannot approve"):
        approve_certificate(token=mcp_token, cert_id=cert_dict["id"])


def test_deny_self_blocked_via_mcp(db, mcp_user, mcp_token, manual_ca):
    result = create_certificate(
        token=mcp_token, ca_id=manual_ca["id"], common_name="self-deny-mcp.example.com",
    )
    import ast
    cert_dict = ast.literal_eval(result)
    with pytest.raises(ValueError, match="Cannot deny"):
        deny_certificate(token=mcp_token, cert_id=cert_dict["id"])
```

- [ ] **Step 2: Add the issue tools to mcp_server.py**

Append to `backend/app/mcp_server.py`:

```python
@mcp.tool()
def create_certificate(
    token: str, ca_id: str, common_name: str,
    organization: str | None = None, org_unit: str | None = None,
    country: str | None = None, state: str | None = None, locality: str | None = None,
    san: list[dict] | None = None, type: str = "server",
    key_algorithm: str = "RSA", key_size: int = 2048,
    validity_days: int | None = None,
    key_usage: list[str] | None = None, extended_key_usage: list[str] | None = None,
) -> str:
    """Create and issue a new certificate. If the CA has auto-approve enabled, the certificate is issued immediately. Otherwise it will be pending approval."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.requester)
        subject = {"CN": common_name}
        if organization:
            subject["O"] = organization
        if org_unit:
            subject["OU"] = org_unit
        if country:
            subject["C"] = country
        if state:
            subject["ST"] = state
        if locality:
            subject["L"] = locality
        data = {
            "ca_id": ca_id, "subject": subject, "san": san or [],
            "type": type, "key_algorithm": key_algorithm,
            "key_size": key_size, "validity_days": validity_days,
        }
        if key_usage:
            data["key_usage"] = key_usage
        if extended_key_usage:
            data["extended_key_usage"] = extended_key_usage
        cert = cert_service.request_certificate(db, user.id, data)
        return str(_cert_to_dict(cert))
    finally:
        db.close()


@mcp.tool()
def submit_csr(
    token: str, ca_id: str, csr_pem: str,
    type: str = "server", validity_days: int | None = None,
) -> str:
    """Submit a PEM-encoded Certificate Signing Request for signing."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.requester)
        data = {"ca_id": ca_id, "csr_pem": csr_pem, "type": type}
        if validity_days:
            data["validity_days"] = validity_days
        cert = cert_service.submit_csr(db, user.id, data)
        return str(_cert_to_dict(cert))
    finally:
        db.close()


@mcp.tool()
def approve_certificate(token: str, cert_id: str) -> str:
    """Approve a pending certificate. Cannot approve a certificate you requested."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator)
        cert = cert_service.approve(db, user.id, cert_id)
        return str(_cert_to_dict(cert))
    finally:
        db.close()


@mcp.tool()
def deny_certificate(token: str, cert_id: str) -> str:
    """Deny a pending certificate. Cannot deny a certificate you requested."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator)
        cert = cert_service.deny(db, user.id, cert_id)
        return str(_cert_to_dict(cert))
    finally:
        db.close()


@mcp.tool()
def download_certificate(
    token: str, cert_id: str, format: str = "pem",
    key_only: bool = False, passphrase: str | None = None,
) -> str:
    """Download a certificate in PEM, DER, or PKCS12 format. Set key_only=true to download only the private key. Passphrase is required for PKCS12."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.requester)
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if user.role == UserRole.requester and cert.requested_by != user.id:
            raise ValueError("Certificate not found")
        data = cert_service.download(cert_id, format, db, passphrase=passphrase, key_only=key_only)
        if format == "pem" or key_only:
            return data.decode() if isinstance(data, bytes) else data
        return base64.b64encode(data).decode()
    finally:
        db.close()
```

- [ ] **Step 3: Run the issue tool tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py -v`

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/mcp_server.py backend/tests/test_mcp.py
git commit -m "feat: add MCP issue tools (create, CSR, approve, deny, download)"
```

---

### Task 5: Mount MCP Server on FastAPI App

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write integration test**

Add to `backend/tests/test_mcp.py`:

```python
def test_mcp_endpoint_exists(client):
    resp = client.get("/mcp")
    assert resp.status_code != 404
```

- [ ] **Step 2: Mount the MCP app in main.py**

In `backend/app/main.py`, add the import after the existing router imports:

```python
from app.mcp_server import mcp
```

After the `app.include_router(templates.router)` line, add:

```python
app.mount("/mcp", mcp.streamable_http_app())
```

- [ ] **Step 3: Run the integration test**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py::test_mcp_endpoint_exists -v`

Expected: PASS (status code is not 404).

- [ ] **Step 4: Run the full test suite to check for regressions**

Run: `cd backend && .venv/bin/python -m pytest tests/ -v --timeout=60`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_mcp.py
git commit -m "feat: mount MCP server at /mcp endpoint"
```

---

### Task 6: Manual Verification and Final Commit

**Files:**
- None new — verify existing work

- [ ] **Step 1: Start the backend and verify the MCP endpoint responds**

Run: `cd backend && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &`

Then test:

```bash
curl -s http://localhost:8000/mcp -X POST -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}'
```

Expected: JSON-RPC response with server info.

- [ ] **Step 2: Stop the dev server**

- [ ] **Step 3: Run the full test suite one final time**

Run: `cd backend && .venv/bin/python -m pytest tests/ -v`

Expected: All tests pass.

- [ ] **Step 4: Final commit and push**

```bash
git add -A
git commit -m "feat: add MCP server for AI agent integration

Embedded Streamable HTTP MCP server at /mcp with API token auth.
11 tools: list/get CAs, list/get/create/approve/deny/download certs,
CSR submission, CA chain, CRL info. Self-approval guard enforced."
git push
```
