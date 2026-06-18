# ACME Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ACME (RFC 8555) server to Certifactory so automated clients (certbot, Caddy) can obtain certificates via the standard ACME protocol, supporting HTTP-01, DNS-01, and TLS-ALPN-01 challenges.

**Architecture:** An embedded FastAPI router under `/acme` (and `/acme/<ca_id>`) backed by three new DB tables (accounts, orders, authorizations) and an `AcmeService`. JWS authentication uses per-account key pairs. Finalization reuses the existing `CertificateService.submit_csr()` + `approve()` pipeline. ACME is purely additive — no existing behavior changes.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, `cryptography` (JWS verification + crypto), `httpx` (HTTP-01), `dnspython` (DNS-01), `ssl` stdlib (TLS-ALPN-01).

## Global Constraints

- Python venv: `backend/.venv` — run python as `.venv/bin/python` from the `backend/` directory.
- Tests: pytest, SQLite test DB. Fixtures (`db`, `client`, `admin_user`, `admin_headers`) live in `backend/tests/conftest.py`.
- Alembic migrations MUST be dialect-aware: use `sa.String()` (not `sa.Enum()`) for status columns to avoid PostgreSQL enum type conflicts; use `server_default=sa.text('false')` for booleans.
- Datetimes stored in DB are naive UTC — use `datetime.now(timezone.utc).replace(tzinfo=None)` or `datetime.utcnow()` when persisting, consistent with the scheduler fix.
- ACME error responses follow RFC 8555 §6.7: JSON body `{"type": "urn:ietf:params:acme:error:<name>", "detail": "...", "status": <code>}` with `Content-Type: application/problem+json`.
- All commits end with the Co-Authored-By trailer used in this repo.
- Run commits from the repo root `/home/jobongo/projects/pki_server`, not `backend/`.

---

### Task 1: Add dnspython dependency

**Files:**
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces: `dnspython` importable as `dns.resolver` in later tasks.

- [ ] **Step 1: Add the dependency**

Add to `backend/requirements.txt` after the `mcp[http]>=1.9.0` line:

```
dnspython>=2.6.0
```

- [ ] **Step 2: Install it**

Run: `cd backend && .venv/bin/pip install "dnspython>=2.6.0"`
Expected: Successful install.

- [ ] **Step 3: Verify import**

Run: `cd backend && .venv/bin/python -c "import dns.resolver; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add dnspython for ACME DNS-01 challenges"
```

---

### Task 2: ACME database models

**Files:**
- Create: `backend/app/models/acme.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_acme_models.py`

**Interfaces:**
- Produces:
  - `AcmeAccount(id, jwk: dict, jwk_thumbprint: str, contact: list, status: str, created_at, updated_at)`
  - `AcmeOrder(id, account_id, ca_id, status: str, identifiers: list, not_before, not_after, certificate_id, expires, created_at)`
  - `AcmeAuthorization(id, order_id, identifier_type: str, identifier_value: str, status: str, challenges: list, expires, created_at)`
  - All three exported from `app.models`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_models.py`:

```python
from datetime import datetime, timezone
from app.models import AcmeAccount, AcmeOrder, AcmeAuthorization


def test_acme_account_persists(db):
    acct = AcmeAccount(jwk={"kty": "RSA", "n": "abc", "e": "AQAB"}, jwk_thumbprint="thumb123", contact=["mailto:a@b.com"], status="active")
    db.add(acct)
    db.commit()
    db.refresh(acct)
    assert acct.id is not None
    assert acct.jwk["kty"] == "RSA"
    assert acct.status == "active"


def test_acme_order_persists(db):
    acct = AcmeAccount(jwk={"kty": "RSA"}, jwk_thumbprint="t1", contact=[], status="active")
    db.add(acct)
    db.commit()
    order = AcmeOrder(account_id=acct.id, ca_id="ca-1", status="pending", identifiers=[{"type": "dns", "value": "example.com"}], expires=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(order)
    db.commit()
    db.refresh(order)
    assert order.id is not None
    assert order.identifiers[0]["value"] == "example.com"
    assert order.certificate_id is None


def test_acme_authorization_persists(db):
    acct = AcmeAccount(jwk={"kty": "RSA"}, jwk_thumbprint="t2", contact=[], status="active")
    db.add(acct)
    db.commit()
    order = AcmeOrder(account_id=acct.id, ca_id="ca-1", status="pending", identifiers=[], expires=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(order)
    db.commit()
    authz = AcmeAuthorization(order_id=order.id, identifier_type="dns", identifier_value="example.com", status="pending", challenges=[{"type": "http-01", "token": "tok", "status": "pending"}], expires=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(authz)
    db.commit()
    db.refresh(authz)
    assert authz.id is not None
    assert authz.challenges[0]["type"] == "http-01"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'AcmeAccount'`.

- [ ] **Step 3: Create the models**

Create `backend/app/models/acme.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AcmeAccount(Base):
    __tablename__ = "acme_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    jwk: Mapped[dict] = mapped_column(JSON, nullable=False)
    jwk_thumbprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    contact: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class AcmeOrder(Base):
    __tablename__ = "acme_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("acme_accounts.id"), nullable=False)
    ca_id: Mapped[str] = mapped_column(String(36), ForeignKey("certificate_authorities.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    identifiers: Mapped[list] = mapped_column(JSON, nullable=False)
    not_before: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    not_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    certificate_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("certificates.id"), nullable=True)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AcmeAuthorization(Base):
    __tablename__ = "acme_authorizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("acme_orders.id"), nullable=False)
    identifier_type: Mapped[str] = mapped_column(String(20), default="dns")
    identifier_value: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    challenges: Mapped[list] = mapped_column(JSON, nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
```

- [ ] **Step 4: Export from models init**

In `backend/app/models/__init__.py`, add after the `from app.models.certificate_template import CertificateTemplate` line:

```python
from app.models.acme import AcmeAccount, AcmeOrder, AcmeAuthorization
```

And add to the `__all__` list, after `"CertificateTemplate",`:

```python
    "AcmeAccount",
    "AcmeOrder",
    "AcmeAuthorization",
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_models.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/acme.py backend/app/models/__init__.py backend/tests/test_acme_models.py
git commit -m "feat: add ACME database models"
```

---

### Task 3: Alembic migration for ACME tables

**Files:**
- Create: `backend/alembic/versions/f6a7b8c9d0e1_add_acme_tables.py`

**Interfaces:**
- Consumes: models from Task 2.
- Produces: migration revision `f6a7b8c9d0e1`, down_revision `e5f6a7b8c9d0`.

- [ ] **Step 1: Confirm the latest revision**

Run: `cd backend && .venv/bin/python -m alembic heads`
Expected: shows `e5f6a7b8c9d0` (the can_self_approve migration). If different, use that value as `down_revision` below.

- [ ] **Step 2: Create the migration**

Create `backend/alembic/versions/f6a7b8c9d0e1_add_acme_tables.py`:

```python
"""add ACME tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'acme_accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('jwk', sa.JSON(), nullable=False),
        sa.Column('jwk_thumbprint', sa.String(64), nullable=False, unique=True),
        sa.Column('contact', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'acme_orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('account_id', sa.String(36), sa.ForeignKey('acme_accounts.id'), nullable=False),
        sa.Column('ca_id', sa.String(36), sa.ForeignKey('certificate_authorities.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('identifiers', sa.JSON(), nullable=False),
        sa.Column('not_before', sa.DateTime(), nullable=True),
        sa.Column('not_after', sa.DateTime(), nullable=True),
        sa.Column('certificate_id', sa.String(36), sa.ForeignKey('certificates.id'), nullable=True),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'acme_authorizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_id', sa.String(36), sa.ForeignKey('acme_orders.id'), nullable=False),
        sa.Column('identifier_type', sa.String(20), nullable=True),
        sa.Column('identifier_value', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('challenges', sa.JSON(), nullable=False),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('acme_authorizations')
    op.drop_table('acme_orders')
    op.drop_table('acme_accounts')
```

- [ ] **Step 3: Run the migration**

Run: `cd backend && .venv/bin/python -m alembic upgrade head`
Expected: `Running upgrade e5f6a7b8c9d0 -> f6a7b8c9d0e1, add ACME tables`.

- [ ] **Step 4: Verify it is reversible**

Run: `cd backend && .venv/bin/python -m alembic downgrade -1 && .venv/bin/python -m alembic upgrade head`
Expected: downgrade then upgrade both succeed.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/f6a7b8c9d0e1_add_acme_tables.py
git commit -m "feat: add Alembic migration for ACME tables"
```

---

### Task 4: ACME settings definitions

**Files:**
- Modify: `backend/app/services/settings_service.py`
- Modify: `backend/app/schemas/settings.py`
- Test: `backend/tests/test_acme_settings.py`

**Interfaces:**
- Consumes: `SettingsService.get(db, key)` / `get_all(db)` existing API.
- Produces: settings keys `acme_enabled` (bool), `acme_default_ca_id` (string), `acme_registration_open` (bool), `acme_allowed_domains` (string), all category `acme`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_settings.py`:

```python
from app.services.settings_service import SettingsService

svc = SettingsService()


def test_acme_settings_defaults(db):
    assert svc.get(db, "acme_enabled") is False
    assert svc.get(db, "acme_default_ca_id") == ""
    assert svc.get(db, "acme_registration_open") is True
    assert svc.get(db, "acme_allowed_domains") == ""


def test_acme_settings_in_category(db):
    defs = svc.get_definitions()
    assert defs["acme_enabled"]["category"] == "acme"
    assert defs["acme_default_ca_id"]["type"] == "string"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_settings.py -v`
Expected: FAIL — `KeyError: 'acme_enabled'`.

- [ ] **Step 3: Add the settings definitions**

In `backend/app/services/settings_service.py`, inside the `SETTINGS_DEFINITIONS` dict, add these entries right before the closing `}` of the dict (after the `mcp_allow_approval` entry):

```python
    "acme_enabled": {
        "type": "bool",
        "default": False,
        "label": "ACME Server Enabled",
        "description": "Allow ACME clients (certbot, Caddy) to request certificates",
        "category": "acme",
    },
    "acme_default_ca_id": {
        "type": "string",
        "default": "",
        "label": "ACME Default CA",
        "description": "CA used for the default /acme/directory endpoint",
        "category": "acme",
    },
    "acme_registration_open": {
        "type": "bool",
        "default": True,
        "label": "ACME Open Registration",
        "description": "Allow new ACME accounts to register",
        "category": "acme",
    },
    "acme_allowed_domains": {
        "type": "string",
        "default": "",
        "label": "ACME Allowed Domains",
        "description": "Comma-separated domain patterns (e.g. *.example.com). Empty allows all.",
        "category": "acme",
    },
```

- [ ] **Step 4: Add string settings to the update schema**

In `backend/app/schemas/settings.py`, add to `SettingsUpdate` (after `crl_regen_interval_minutes: int | None = None`):

```python
    acme_enabled: bool | None = None
    acme_default_ca_id: str | None = None
    acme_registration_open: bool | None = None
    acme_allowed_domains: str | None = None
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_settings.py -v`
Expected: PASS (2 tests).

Note: the existing `_serialize`/`_cast` in SettingsService already handle `string` type (returns raw). No change needed there.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/settings_service.py backend/app/schemas/settings.py backend/tests/test_acme_settings.py
git commit -m "feat: add ACME settings definitions"
```

---

### Task 5: JWS validation utility

**Files:**
- Create: `backend/app/services/acme_jws.py`
- Test: `backend/tests/test_acme_jws.py`

**Interfaces:**
- Produces:
  - `jwk_thumbprint(jwk: dict) -> str` — RFC 7638 SHA-256 thumbprint, base64url, no padding.
  - `verify_jws(protected: dict, payload_b64: str, signature_b64: str, jwk: dict) -> bool` — verifies a flattened JWS signature.
  - `decode_protected(protected_b64: str) -> dict` — base64url-decode + JSON parse.
  - `b64url_decode(s: str) -> bytes` and `b64url_encode(b: bytes) -> str` helpers (no padding).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_jws.py`:

```python
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes

from app.services.acme_jws import jwk_thumbprint, verify_jws, decode_protected, b64url_encode, b64url_decode


def _rsa_jwk(public_key):
    nums = public_key.public_numbers()
    def to_b64(n):
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return b64url_encode(b)
    return {"kty": "RSA", "n": to_b64(nums.n), "e": to_b64(nums.e)}


def test_b64url_roundtrip():
    assert b64url_decode(b64url_encode(b"hello")) == b"hello"


def test_jwk_thumbprint_is_stable():
    jwk = {"kty": "RSA", "n": "abc", "e": "AQAB"}
    t1 = jwk_thumbprint(jwk)
    t2 = jwk_thumbprint(jwk)
    assert t1 == t2
    assert "=" not in t1  # no padding


def test_verify_jws_accepts_valid_signature():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    protected = {"alg": "RS256", "nonce": "n1", "url": "https://x/acme/new-order"}
    payload = {"identifiers": [{"type": "dns", "value": "example.com"}]}
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(json.dumps(payload).encode())
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    from cryptography.hazmat.primitives.asymmetric import padding
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = b64url_encode(sig)
    assert verify_jws(protected, payload_b64, sig_b64, jwk, protected_b64=protected_b64) is True


def test_verify_jws_rejects_tampered_payload():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    protected = {"alg": "RS256", "nonce": "n1", "url": "https://x"}
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(json.dumps({"a": 1}).encode())
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    from cryptography.hazmat.primitives.asymmetric import padding
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = b64url_encode(sig)
    tampered = b64url_encode(json.dumps({"a": 2}).encode())
    assert verify_jws(protected, tampered, sig_b64, jwk, protected_b64=protected_b64) is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_jws.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.acme_jws'`.

- [ ] **Step 3: Implement the JWS utility**

Create `backend/app/services/acme_jws.py`:

```python
import base64
import hashlib
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, ec, utils
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers, SECP256R1, SECP384R1, SECP521R1
from cryptography.exceptions import InvalidSignature


def b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def decode_protected(protected_b64: str) -> dict:
    return json.loads(b64url_decode(protected_b64))


def jwk_thumbprint(jwk: dict) -> str:
    # RFC 7638 — canonical JSON of required members in lexicographic order
    if jwk["kty"] == "RSA":
        canonical = {"e": jwk["e"], "kty": "RSA", "n": jwk["n"]}
    elif jwk["kty"] == "EC":
        canonical = {"crv": jwk["crv"], "kty": "EC", "x": jwk["x"], "y": jwk["y"]}
    else:
        raise ValueError(f"Unsupported key type: {jwk['kty']}")
    data = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    return b64url_encode(hashlib.sha256(data).digest())


def _public_key_from_jwk(jwk: dict):
    if jwk["kty"] == "RSA":
        n = int.from_bytes(b64url_decode(jwk["n"]), "big")
        e = int.from_bytes(b64url_decode(jwk["e"]), "big")
        return RSAPublicNumbers(e, n).public_key()
    if jwk["kty"] == "EC":
        curves = {"P-256": SECP256R1(), "P-384": SECP384R1(), "P-521": SECP521R1()}
        curve = curves[jwk["crv"]]
        x = int.from_bytes(b64url_decode(jwk["x"]), "big")
        y = int.from_bytes(b64url_decode(jwk["y"]), "big")
        return EllipticCurvePublicNumbers(x, y, curve).public_key()
    raise ValueError(f"Unsupported key type: {jwk['kty']}")


def verify_jws(protected: dict, payload_b64: str, signature_b64: str, jwk: dict, protected_b64: str) -> bool:
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    signature = b64url_decode(signature_b64)
    try:
        public_key = _public_key_from_jwk(jwk)
        alg = protected.get("alg", "")
        if alg.startswith("RS"):
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
        elif alg.startswith("ES"):
            # JWS ES* uses raw r||s; convert to DER for cryptography
            half = len(signature) // 2
            r = int.from_bytes(signature[:half], "big")
            s = int.from_bytes(signature[half:], "big")
            der_sig = utils.encode_dss_signature(r, s)
            hash_alg = {"ES256": hashes.SHA256(), "ES384": hashes.SHA384(), "ES512": hashes.SHA512()}[alg]
            public_key.verify(der_sig, signing_input, ec.ECDSA(hash_alg))
        else:
            return False
        return True
    except (InvalidSignature, ValueError, KeyError):
        return False
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_jws.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/acme_jws.py backend/tests/test_acme_jws.py
git commit -m "feat: add ACME JWS verification utility"
```

---

### Task 6: Nonce manager

**Files:**
- Create: `backend/app/services/acme_nonce.py`
- Test: `backend/tests/test_acme_nonce.py`

**Interfaces:**
- Produces: `NonceManager` class with `issue() -> str` and `consume(nonce: str) -> bool`. Module-level singleton `nonce_manager = NonceManager()`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_nonce.py`:

```python
from app.services.acme_nonce import NonceManager


def test_issued_nonce_can_be_consumed_once():
    mgr = NonceManager()
    n = mgr.issue()
    assert mgr.consume(n) is True
    assert mgr.consume(n) is False  # already used


def test_unknown_nonce_rejected():
    mgr = NonceManager()
    assert mgr.consume("never-issued") is False


def test_nonces_are_unique():
    mgr = NonceManager()
    nonces = {mgr.issue() for _ in range(100)}
    assert len(nonces) == 100
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_nonce.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the nonce manager**

Create `backend/app/services/acme_nonce.py`:

```python
import secrets
import time

_TTL_SECONDS = 3600


class NonceManager:
    def __init__(self):
        self._nonces: dict[str, float] = {}

    def _prune(self):
        cutoff = time.monotonic() - _TTL_SECONDS
        expired = [n for n, t in self._nonces.items() if t < cutoff]
        for n in expired:
            del self._nonces[n]

    def issue(self) -> str:
        self._prune()
        nonce = secrets.token_urlsafe(32)
        self._nonces[nonce] = time.monotonic()
        return nonce

    def consume(self, nonce: str) -> bool:
        if nonce in self._nonces:
            del self._nonces[nonce]
            return True
        return False


nonce_manager = NonceManager()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_nonce.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/acme_nonce.py backend/tests/test_acme_nonce.py
git commit -m "feat: add ACME nonce manager"
```

---

### Task 7: Challenge validators

**Files:**
- Create: `backend/app/services/acme_challenges.py`
- Test: `backend/tests/test_acme_challenges.py`

**Interfaces:**
- Consumes: `jwk_thumbprint` from `acme_jws`.
- Produces:
  - `key_authorization(token: str, jwk: dict) -> str` — returns `f"{token}.{jwk_thumbprint(jwk)}"`.
  - `dns_txt_value(token: str, jwk: dict) -> str` — base64url(sha256(key_authorization)).
  - `validate_http_01(domain: str, token: str, jwk: dict) -> bool` — fetches the well-known URL.
  - `validate_dns_01(domain: str, token: str, jwk: dict) -> bool` — DNS TXT lookup.
  - `validate_tls_alpn_01(domain: str, token: str, jwk: dict) -> bool` — TLS-ALPN connection check.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_challenges.py`:

```python
import hashlib
from unittest.mock import patch, MagicMock

from app.services.acme_challenges import key_authorization, dns_txt_value, validate_http_01, validate_dns_01
from app.services.acme_jws import jwk_thumbprint, b64url_encode

JWK = {"kty": "RSA", "n": "abc", "e": "AQAB"}


def test_key_authorization_format():
    ka = key_authorization("mytoken", JWK)
    assert ka == f"mytoken.{jwk_thumbprint(JWK)}"


def test_dns_txt_value_is_sha256_of_key_auth():
    ka = key_authorization("mytoken", JWK)
    expected = b64url_encode(hashlib.sha256(ka.encode()).digest())
    assert dns_txt_value("mytoken", JWK) == expected


def test_validate_http_01_success():
    ka = key_authorization("tok", JWK)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = ka
    with patch("app.services.acme_challenges.httpx.get", return_value=mock_resp):
        assert validate_http_01("example.com", "tok", JWK) is True


def test_validate_http_01_wrong_content():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "wrong"
    with patch("app.services.acme_challenges.httpx.get", return_value=mock_resp):
        assert validate_http_01("example.com", "tok", JWK) is False


def test_validate_dns_01_success():
    expected = dns_txt_value("tok", JWK)
    mock_answer = MagicMock()
    mock_answer.strings = [expected.encode()]
    with patch("app.services.acme_challenges.dns.resolver.resolve", return_value=[mock_answer]):
        assert validate_dns_01("example.com", "tok", JWK) is True


def test_validate_dns_01_no_match():
    mock_answer = MagicMock()
    mock_answer.strings = [b"some-other-value"]
    with patch("app.services.acme_challenges.dns.resolver.resolve", return_value=[mock_answer]):
        assert validate_dns_01("example.com", "tok", JWK) is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_challenges.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the validators**

Create `backend/app/services/acme_challenges.py`:

```python
import hashlib
import socket
import ssl

import httpx
import dns.resolver

from app.services.acme_jws import jwk_thumbprint, b64url_encode

_HTTP_TIMEOUT = 10
_ACME_EXTENSION_OID = "1.3.6.1.5.5.7.1.31"


def key_authorization(token: str, jwk: dict) -> str:
    return f"{token}.{jwk_thumbprint(jwk)}"


def dns_txt_value(token: str, jwk: dict) -> str:
    ka = key_authorization(token, jwk)
    return b64url_encode(hashlib.sha256(ka.encode()).digest())


def validate_http_01(domain: str, token: str, jwk: dict) -> bool:
    expected = key_authorization(token, jwk)
    url = f"http://{domain}/.well-known/acme-challenge/{token}"
    try:
        resp = httpx.get(url, timeout=_HTTP_TIMEOUT, follow_redirects=True)
        if resp.status_code != 200:
            return False
        return resp.text.strip() == expected
    except Exception:
        return False


def validate_dns_01(domain: str, token: str, jwk: dict) -> bool:
    expected = dns_txt_value(token, jwk)
    record_name = f"_acme-challenge.{domain}"
    try:
        answers = dns.resolver.resolve(record_name, "TXT")
        for rdata in answers:
            for txt in rdata.strings:
                value = txt.decode() if isinstance(txt, bytes) else txt
                if value == expected:
                    return True
        return False
    except Exception:
        return False


def validate_tls_alpn_01(domain: str, token: str, jwk: dict) -> bool:
    ka = key_authorization(token, jwk)
    expected_digest = hashlib.sha256(ka.encode()).digest()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_alpn_protocols(["acme-tls/1"])
    try:
        with socket.create_connection((domain, 443), timeout=_HTTP_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                der = ssock.getpeercert(binary_form=True)
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        for ext in cert.extensions:
            if ext.oid.dotted_string == _ACME_EXTENSION_OID:
                ext_bytes = ext.value.value if hasattr(ext.value, "value") else bytes(ext.value.public_bytes())
                return expected_digest in ext_bytes
        return False
    except Exception:
        return False
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_challenges.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/acme_challenges.py backend/tests/test_acme_challenges.py
git commit -m "feat: add ACME challenge validators (HTTP-01, DNS-01, TLS-ALPN-01)"
```

---

### Task 8: AcmeService — accounts and system user

**Files:**
- Create: `backend/app/services/acme_service.py`
- Test: `backend/tests/test_acme_service_accounts.py`

**Interfaces:**
- Consumes: `AcmeAccount` model; `jwk_thumbprint` from `acme_jws`.
- Produces `AcmeService` with:
  - `get_system_user_id(db) -> str` — returns id of an auto-created `acme-service` user (role requester, can_self_approve False), creating it if missing.
  - `get_or_create_account(db, jwk: dict, contact: list | None, only_return_existing: bool) -> AcmeAccount` — raises `ValueError("accountDoesNotExist")` if `only_return_existing` and not found.
  - `get_account_by_thumbprint(db, thumbprint: str) -> AcmeAccount | None`.
  - `domain_allowed(allowed_domains: str, domain: str) -> bool` — matches comma-separated patterns, supports `*.example.com` wildcards; empty allows all.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_service_accounts.py`:

```python
import pytest
from app.services.acme_service import AcmeService

svc = AcmeService()
JWK = {"kty": "RSA", "n": "abc", "e": "AQAB"}


def test_system_user_created_once(db):
    uid1 = svc.get_system_user_id(db)
    uid2 = svc.get_system_user_id(db)
    assert uid1 == uid2
    from app.models import User
    user = db.query(User).filter(User.id == uid1).first()
    assert user.username == "acme-service"


def test_get_or_create_account_creates(db):
    acct = svc.get_or_create_account(db, JWK, ["mailto:a@b.com"], only_return_existing=False)
    assert acct.id is not None
    assert acct.contact == ["mailto:a@b.com"]


def test_get_or_create_account_returns_existing(db):
    a1 = svc.get_or_create_account(db, JWK, None, only_return_existing=False)
    a2 = svc.get_or_create_account(db, JWK, None, only_return_existing=False)
    assert a1.id == a2.id


def test_only_return_existing_raises_when_missing(db):
    with pytest.raises(ValueError, match="accountDoesNotExist"):
        svc.get_or_create_account(db, {"kty": "RSA", "n": "zzz", "e": "AQAB"}, None, only_return_existing=True)


def test_domain_allowed_empty_allows_all():
    assert svc.domain_allowed("", "anything.com") is True


def test_domain_allowed_exact_match():
    assert svc.domain_allowed("example.com,test.com", "example.com") is True
    assert svc.domain_allowed("example.com", "other.com") is False


def test_domain_allowed_wildcard():
    assert svc.domain_allowed("*.example.com", "www.example.com") is True
    assert svc.domain_allowed("*.example.com", "example.com") is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_service_accounts.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement AcmeService accounts portion**

Create `backend/app/services/acme_service.py`:

```python
import fnmatch

from sqlalchemy.orm import Session

from app.models import AcmeAccount, User, UserRole
from app.services.acme_jws import jwk_thumbprint
from app.services.auth_service import AuthService

auth_service = AuthService()

_SYSTEM_USERNAME = "acme-service"


class AcmeService:
    def get_system_user_id(self, db: Session) -> str:
        user = db.query(User).filter(User.username == _SYSTEM_USERNAME).first()
        if user:
            return user.id
        import secrets as _secrets
        user = User(
            username=_SYSTEM_USERNAME,
            email="acme-service@certifactory.local",
            password_hash=auth_service.hash_password(_secrets.token_urlsafe(32)),
            role=UserRole.requester,
            is_active=True,
            can_self_approve=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id

    def get_account_by_thumbprint(self, db: Session, thumbprint: str) -> AcmeAccount | None:
        return db.query(AcmeAccount).filter(AcmeAccount.jwk_thumbprint == thumbprint).first()

    def get_or_create_account(self, db: Session, jwk: dict, contact: list | None, only_return_existing: bool) -> AcmeAccount:
        thumbprint = jwk_thumbprint(jwk)
        existing = self.get_account_by_thumbprint(db, thumbprint)
        if existing:
            return existing
        if only_return_existing:
            raise ValueError("accountDoesNotExist")
        account = AcmeAccount(jwk=jwk, jwk_thumbprint=thumbprint, contact=contact, status="active")
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def domain_allowed(self, allowed_domains: str, domain: str) -> bool:
        patterns = [p.strip() for p in allowed_domains.split(",") if p.strip()]
        if not patterns:
            return True
        return any(fnmatch.fnmatch(domain, pattern) for pattern in patterns)


acme_service = AcmeService()
```

Note: `password_hash` is set to a random unusable value — the account can never log in via password since ACME uses key-based auth. `AuthService.hash_password` is the existing method used in conftest.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_service_accounts.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/acme_service.py backend/tests/test_acme_service_accounts.py
git commit -m "feat: add AcmeService account management and domain matching"
```

---

### Task 9: AcmeService — orders and authorizations

**Files:**
- Modify: `backend/app/services/acme_service.py`
- Test: `backend/tests/test_acme_service_orders.py`

**Interfaces:**
- Consumes: `AcmeOrder`, `AcmeAuthorization` models; `secrets` for tokens.
- Produces, added to `AcmeService`:
  - `create_order(db, account_id, ca_id, identifiers: list, not_before, not_after) -> AcmeOrder` — also creates one AcmeAuthorization per identifier, each with three challenges (http-01, dns-01, tls-alpn-01) carrying random tokens.
  - `get_order(db, order_id) -> AcmeOrder | None`.
  - `get_authorization(db, authz_id) -> AcmeAuthorization | None`.
  - `list_authorizations(db, order_id) -> list[AcmeAuthorization]`.
  - `new_token() -> str` — base64url 32-byte token.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_service_orders.py`:

```python
from datetime import datetime, timezone
from app.services.acme_service import AcmeService
from app.models import AcmeAuthorization

svc = AcmeService()
JWK = {"kty": "RSA", "n": "ord", "e": "AQAB"}


def _account(db):
    return svc.get_or_create_account(db, JWK, None, only_return_existing=False)


def test_create_order_creates_authorizations(db):
    acct = _account(db)
    order = svc.create_order(db, acct.id, "ca-1", [{"type": "dns", "value": "a.com"}, {"type": "dns", "value": "b.com"}], None, None)
    assert order.status == "pending"
    authzs = svc.list_authorizations(db, order.id)
    assert len(authzs) == 2
    values = {a.identifier_value for a in authzs}
    assert values == {"a.com", "b.com"}


def test_each_authorization_has_three_challenges(db):
    acct = _account(db)
    order = svc.create_order(db, acct.id, "ca-1", [{"type": "dns", "value": "c.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    types = {c["type"] for c in authz.challenges}
    assert types == {"http-01", "dns-01", "tls-alpn-01"}
    for c in authz.challenges:
        assert c["status"] == "pending"
        assert len(c["token"]) > 10


def test_get_order_and_authorization(db):
    acct = _account(db)
    order = svc.create_order(db, acct.id, "ca-1", [{"type": "dns", "value": "d.com"}], None, None)
    assert svc.get_order(db, order.id).id == order.id
    authz = svc.list_authorizations(db, order.id)[0]
    assert svc.get_authorization(db, authz.id).identifier_value == "d.com"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_service_orders.py -v`
Expected: FAIL — `AttributeError: 'AcmeService' object has no attribute 'create_order'`.

- [ ] **Step 3: Add order methods to AcmeService**

In `backend/app/services/acme_service.py`, add these imports at the top (merge with existing imports):

```python
import secrets
from datetime import datetime, timedelta, timezone

from app.models import AcmeOrder, AcmeAuthorization
from app.services.acme_jws import b64url_encode
```

Add these methods inside the `AcmeService` class (before the closing of the class):

```python
    def new_token(self) -> str:
        return b64url_encode(secrets.token_bytes(32))

    def _now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def create_order(self, db: Session, account_id: str, ca_id: str, identifiers: list, not_before, not_after) -> AcmeOrder:
        expires = self._now() + timedelta(days=7)
        order = AcmeOrder(
            account_id=account_id, ca_id=ca_id, status="pending",
            identifiers=identifiers, not_before=not_before, not_after=not_after,
            expires=expires,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        for ident in identifiers:
            challenges = [
                {"type": ctype, "token": self.new_token(), "status": "pending", "validated": None, "error": None}
                for ctype in ("http-01", "dns-01", "tls-alpn-01")
            ]
            authz = AcmeAuthorization(
                order_id=order.id, identifier_type=ident["type"], identifier_value=ident["value"],
                status="pending", challenges=challenges, expires=expires,
            )
            db.add(authz)
        db.commit()
        return order

    def get_order(self, db: Session, order_id: str) -> AcmeOrder | None:
        return db.query(AcmeOrder).filter(AcmeOrder.id == order_id).first()

    def get_authorization(self, db: Session, authz_id: str) -> AcmeAuthorization | None:
        return db.query(AcmeAuthorization).filter(AcmeAuthorization.id == authz_id).first()

    def list_authorizations(self, db: Session, order_id: str) -> list:
        return db.query(AcmeAuthorization).filter(AcmeAuthorization.order_id == order_id).all()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_service_orders.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/acme_service.py backend/tests/test_acme_service_orders.py
git commit -m "feat: add ACME order and authorization creation"
```

---

### Task 10: AcmeService — challenge processing and finalization

**Files:**
- Modify: `backend/app/services/acme_service.py`
- Test: `backend/tests/test_acme_service_finalize.py`

**Interfaces:**
- Consumes: challenge validators from `acme_challenges`; `CertificateService.submit_csr` and `approve`; `CryptoService.der_to_pem` for CSR (note: CSR is DER → use `x509.load_der_x509_csr`).
- Produces, added to `AcmeService`:
  - `process_challenge(db, authz_id, challenge_type, jwk: dict) -> AcmeAuthorization` — runs the matching validator; on success marks challenge+authz valid and promotes order to `ready` if all authz valid; on failure marks invalid.
  - `finalize_order(db, order_id, csr_der: bytes) -> AcmeOrder` — validates order is `ready`, converts DER CSR to PEM, checks CSR domains == order identifiers, issues via CertificateService, links cert, sets order `valid`.
  - `get_order_certificate_pem(db, order_id) -> str` — returns end-entity PEM + CA chain concatenated.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_service_finalize.py`:

```python
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.services.acme_service import AcmeService
from app.services.crypto_service import CryptoService

svc = AcmeService()
crypto = CryptoService()
JWK = {"kty": "RSA", "n": "fin", "e": "AQAB"}


def _csr_der(domain):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.DER)


def _ca(db):
    from app.routers.cas import ca_service as real_ca_service
    data = {
        "name": "ACME CA", "description": None, "subject": {"CN": "ACME CA"},
        "key_algorithm": "RSA", "key_size": 2048, "validity_days": 3650,
        "max_path_length": None, "auto_approve": True,
        "crl_distribution_url": None, "ocsp_url": None,
    }
    from app.models import User, UserRole
    from app.services.auth_service import AuthService
    admin = User(username="acmeadmin", email="acmeadmin@t.com", password_hash=AuthService().hash_password("x"), role=UserRole.admin)
    db.add(admin); db.commit(); db.refresh(admin)
    return real_ca_service.create_root_ca(db, admin.id, data)


def test_process_challenge_success_marks_ready(db):
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, "ca-x", [{"type": "dns", "value": "valid.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        updated = svc.process_challenge(db, authz.id, "http-01", JWK)
    assert updated.status == "valid"
    assert svc.get_order(db, order.id).status == "ready"


def test_process_challenge_failure_marks_invalid(db):
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, "ca-x", [{"type": "dns", "value": "bad.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=False):
        updated = svc.process_challenge(db, authz.id, "http-01", JWK)
    assert updated.status == "invalid"


def test_finalize_issues_certificate(db):
    ca = _ca(db)
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, ca.id, [{"type": "dns", "value": "finalize.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        svc.process_challenge(db, authz.id, "http-01", JWK)
    order = svc.finalize_order(db, order.id, _csr_der("finalize.com"))
    assert order.status == "valid"
    assert order.certificate_id is not None
    pem = svc.get_order_certificate_pem(db, order.id)
    assert "BEGIN CERTIFICATE" in pem


def test_finalize_rejects_domain_mismatch(db):
    import pytest
    ca = _ca(db)
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, ca.id, [{"type": "dns", "value": "ordered.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        svc.process_challenge(db, authz.id, "http-01", JWK)
    with pytest.raises(ValueError, match="badCSR"):
        svc.finalize_order(db, order.id, _csr_der("different.com"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_service_finalize.py -v`
Expected: FAIL — `process_challenge` missing.

- [ ] **Step 3: Add challenge processing and finalize methods**

In `backend/app/services/acme_service.py`, add imports (merge with existing):

```python
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from app.models import Certificate, CertificateAuthority
from app.services.acme_challenges import validate_http_01, validate_dns_01, validate_tls_alpn_01
from app.services.ca_service import CAService
from app.services.certificate_service import CertificateService

cert_service = CertificateService()
ca_svc = CAService()
```

Add these methods inside `AcmeService`:

```python
    def process_challenge(self, db: Session, authz_id: str, challenge_type: str, jwk: dict):
        authz = self.get_authorization(db, authz_id)
        if not authz:
            raise ValueError("malformed")
        validators = {
            "http-01": validate_http_01,
            "dns-01": validate_dns_01,
            "tls-alpn-01": validate_tls_alpn_01,
        }
        validator = validators.get(challenge_type)
        if not validator:
            raise ValueError("malformed")
        token = None
        challenges = list(authz.challenges)
        for ch in challenges:
            if ch["type"] == challenge_type:
                token = ch["token"]
        if token is None:
            raise ValueError("malformed")

        ok = validator(authz.identifier_value, token, jwk)
        for ch in challenges:
            if ch["type"] == challenge_type:
                ch["status"] = "valid" if ok else "invalid"
                ch["validated"] = self._now().isoformat() if ok else None
                ch["error"] = None if ok else "Validation failed"
        authz.challenges = challenges
        authz.status = "valid" if ok else "invalid"
        db.commit()
        db.refresh(authz)

        if ok:
            order = self.get_order(db, authz.order_id)
            authzs = self.list_authorizations(db, order.id)
            if all(a.status == "valid" for a in authzs):
                order.status = "ready"
                db.commit()
        return authz

    def finalize_order(self, db: Session, order_id: str, csr_der: bytes):
        order = self.get_order(db, order_id)
        if not order:
            raise ValueError("malformed")
        if order.status != "ready":
            raise ValueError("orderNotReady")

        try:
            csr = x509.load_der_x509_csr(csr_der)
        except Exception:
            raise ValueError("badCSR")
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

        csr_domains = set()
        try:
            san = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            for name in san.value:
                if isinstance(name, x509.DNSName):
                    csr_domains.add(name.value)
        except x509.ExtensionNotFound:
            pass
        for attr in csr.subject:
            if attr.oid == x509.oid.NameOID.COMMON_NAME:
                csr_domains.add(attr.value)

        order_domains = {i["value"] for i in order.identifiers}
        if csr_domains != order_domains:
            raise ValueError("badCSR")

        order.status = "processing"
        db.commit()

        system_user_id = self.get_system_user_id(db)
        cert = cert_service.submit_csr(db, system_user_id, {
            "ca_id": order.ca_id, "csr_pem": csr_pem, "type": "server",
        })
        from app.models import CertificateStatus
        if cert.status == CertificateStatus.pending:
            cert = cert_service.approve(db, system_user_id, cert.id, _skip_self_check=True)

        order.certificate_id = cert.id
        order.status = "valid"
        db.commit()
        db.refresh(order)
        return order

    def get_order_certificate_pem(self, db: Session, order_id: str) -> str:
        order = self.get_order(db, order_id)
        if not order or not order.certificate_id:
            raise ValueError("malformed")
        cert = db.query(Certificate).filter(Certificate.id == order.certificate_id).first()
        if not cert or not cert.certificate_pem:
            raise ValueError("malformed")
        chain = ca_svc.get_chain(db, order.ca_id)
        parts = [cert.certificate_pem.strip()] + [c.strip() for c in chain]
        return "\n".join(parts) + "\n"
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_service_finalize.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the whole ACME service suite for regressions**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_service_accounts.py tests/test_acme_service_orders.py tests/test_acme_service_finalize.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/acme_service.py backend/tests/test_acme_service_finalize.py
git commit -m "feat: add ACME challenge processing and order finalization"
```

---

### Task 11: ACME router — directory, nonce, and JWS request helper

**Files:**
- Create: `backend/app/routers/acme.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_acme_router_basic.py`

**Interfaces:**
- Consumes: `acme_service`, `nonce_manager`, `settings_service`, JWS helpers.
- Produces: `router` (APIRouter, prefix `/acme`) registered in `main.py`. Directory at `GET /acme/directory` and `GET /acme/{ca_id}/directory`; nonce at `HEAD/GET /acme/new-nonce`.
- Produces helper `_resolve_ca_id(db, ca_id: str | None) -> str` and `_acme_error(error_type, detail, status)` used in later tasks.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_router_basic.py`:

```python
def _enable_acme(db, ca_id="some-ca"):
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value=ca_id))
    db.commit()


def test_directory_returns_endpoints(client, db):
    _enable_acme(db)
    resp = client.get("/acme/directory")
    assert resp.status_code == 200
    body = resp.json()
    assert body["newNonce"].endswith("/acme/new-nonce")
    assert "newAccount" in body
    assert "newOrder" in body


def test_directory_disabled_returns_403(client, db):
    resp = client.get("/acme/directory")
    assert resp.status_code == 403


def test_new_nonce_returns_replay_nonce_header(client, db):
    _enable_acme(db)
    resp = client.head("/acme/new-nonce")
    assert resp.status_code == 200
    assert "Replay-Nonce" in resp.headers
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_router_basic.py -v`
Expected: FAIL — 404 (router not registered).

- [ ] **Step 3: Create the router with directory + nonce**

Create `backend/app/routers/acme.py`:

```python
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.acme_service import acme_service
from app.services.acme_nonce import nonce_manager
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/acme", tags=["acme"])
settings_service = SettingsService()

_PROBLEM = "application/problem+json"
_ERROR_PREFIX = "urn:ietf:params:acme:error:"


def _acme_error(error_type: str, detail: str, status: int) -> JSONResponse:
    resp = JSONResponse(
        status_code=status,
        content={"type": f"{_ERROR_PREFIX}{error_type}", "detail": detail, "status": status},
        media_type=_PROBLEM,
    )
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


def _require_enabled(db: Session):
    if not settings_service.get(db, "acme_enabled"):
        return False
    return True


def _resolve_ca_id(db: Session, ca_id: str | None) -> str | None:
    if ca_id:
        return ca_id
    default = settings_service.get(db, "acme_default_ca_id")
    return default or None


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _directory_body(request: Request, prefix: str) -> dict:
    base = _base_url(request)
    return {
        "newNonce": f"{base}{prefix}/new-nonce",
        "newAccount": f"{base}{prefix}/new-account",
        "newOrder": f"{base}{prefix}/new-order",
        "revokeCert": f"{base}{prefix}/revoke-cert",
        "keyChange": f"{base}{prefix}/key-change",
    }


@router.get("/directory")
def directory(request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    resp = JSONResponse(content=_directory_body(request, "/acme"))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.get("/{ca_id}/directory")
def directory_for_ca(ca_id: str, request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    resp = JSONResponse(content=_directory_body(request, f"/acme/{ca_id}"))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.api_route("/new-nonce", methods=["GET", "HEAD"])
def new_nonce(db: Session = Depends(get_db)):
    resp = Response(status_code=200)
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    resp.headers["Cache-Control"] = "no-store"
    return resp
```

- [ ] **Step 4: Register the router in main.py**

In `backend/app/main.py`, add to the routers import line:

```python
from app.routers import auth, users, audit, cas, certificates, crl, ocsp, dashboard, tokens, settings as settings_router, templates, tls, acme
```

And after `app.include_router(tls.router)`:

```python
app.include_router(acme.router)
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_router_basic.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/acme.py backend/app/main.py backend/tests/test_acme_router_basic.py
git commit -m "feat: add ACME directory and nonce endpoints"
```

---

### Task 12: ACME router — JWS request parsing helper

**Files:**
- Modify: `backend/app/routers/acme.py`
- Test: `backend/tests/test_acme_jws_request.py`

**Interfaces:**
- Consumes: `nonce_manager`, `verify_jws`, `decode_protected`, `b64url_decode`, `acme_service`.
- Produces in `acme.py`: `parse_jws_request(request, db, expect_jwk: bool) -> tuple[dict, dict, dict]` returning `(protected, payload, jwk)`. Raises a custom `AcmeError(error_type, detail, status)` exception on failure. Adds `AcmeError` exception class and a handler that converts it to a problem+json response.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_jws_request.py`:

```python
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

from app.services.acme_jws import b64url_encode


def _rsa_jwk(public_key):
    nums = public_key.public_numbers()
    def to_b64(n):
        return b64url_encode(n.to_bytes((n.bit_length() + 7) // 8, "big"))
    return {"kty": "RSA", "n": to_b64(nums.n), "e": to_b64(nums.e)}


def _signed_jws(key, jwk, url, nonce, payload_obj, kid=None):
    protected = {"alg": "RS256", "nonce": nonce, "url": url}
    if kid:
        protected["kid"] = kid
    else:
        protected["jwk"] = jwk
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(json.dumps(payload_obj).encode()) if payload_obj is not None else ""
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return {"protected": protected_b64, "payload": payload_b64, "signature": b64url_encode(sig)}


def _enable(db):
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value="ca-1"))
    db.commit()


def test_new_account_with_valid_jws(client, db):
    _enable(db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    url = "http://testserver/acme/new-account"
    body = _signed_jws(key, jwk, url, nonce, {"contact": ["mailto:a@b.com"], "termsOfServiceAgreed": True})
    resp = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code in (200, 201)
    assert "Replay-Nonce" in resp.headers


def test_bad_nonce_rejected(client, db):
    _enable(db)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    url = "http://testserver/acme/new-account"
    body = _signed_jws(key, jwk, url, "fake-nonce", {"termsOfServiceAgreed": True})
    resp = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 400
    assert "badNonce" in resp.json()["type"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_jws_request.py -v`
Expected: FAIL — `/acme/new-account` returns 404 (not implemented yet).

- [ ] **Step 3: Add AcmeError, the JWS parser, and a stub new-account**

In `backend/app/routers/acme.py`, add after the imports:

```python
from app.services.acme_jws import verify_jws, decode_protected, b64url_decode, jwk_thumbprint
import json


class AcmeError(Exception):
    def __init__(self, error_type: str, detail: str, status: int):
        self.error_type = error_type
        self.detail = detail
        self.status = status
```

Add the parser function (after `_resolve_ca_id`):

```python
async def parse_jws_request(request: Request, db: Session, expect_jwk: bool):
    try:
        body = await request.json()
    except Exception:
        raise AcmeError("malformed", "Request body is not valid JSON", 400)

    protected_b64 = body.get("protected")
    payload_b64 = body.get("payload", "")
    signature_b64 = body.get("signature")
    if not protected_b64 or signature_b64 is None:
        raise AcmeError("malformed", "Missing JWS fields", 400)

    try:
        protected = decode_protected(protected_b64)
    except Exception:
        raise AcmeError("malformed", "Invalid protected header", 400)

    nonce = protected.get("nonce")
    if not nonce or not nonce_manager.consume(nonce):
        raise AcmeError("badNonce", "Invalid or missing nonce", 400)

    if expect_jwk:
        jwk = protected.get("jwk")
        if not jwk:
            raise AcmeError("malformed", "Expected jwk in protected header", 400)
    else:
        kid = protected.get("kid")
        if not kid:
            raise AcmeError("malformed", "Expected kid in protected header", 400)
        account_id = kid.rstrip("/").split("/")[-1]
        from app.models import AcmeAccount
        account = db.query(AcmeAccount).filter(AcmeAccount.id == account_id).first()
        if not account:
            raise AcmeError("accountDoesNotExist", "Unknown account", 400)
        jwk = account.jwk

    if not verify_jws(protected, payload_b64, signature_b64, jwk, protected_b64=protected_b64):
        raise AcmeError("unauthorized", "JWS signature verification failed", 401)

    if payload_b64 == "":
        payload = {}
    else:
        try:
            payload = json.loads(b64url_decode(payload_b64))
        except Exception:
            raise AcmeError("malformed", "Invalid payload", 400)

    return protected, payload, jwk
```

Register an exception handler. In `backend/app/routers/acme.py` this can't use `@app.exception_handler`, so convert AcmeError inside each endpoint. Add a helper:

```python
def _error_response(e: AcmeError) -> JSONResponse:
    return _acme_error(e.error_type, e.detail, e.status)
```

Add a stub `new-account` endpoint to make the test pass:

```python
@router.post("/new-account")
async def new_account(request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=True)
    except AcmeError as e:
        return _error_response(e)

    only_existing = payload.get("onlyReturnExisting", False)
    try:
        if not settings_service.get(db, "acme_registration_open") and not only_existing:
            existing = acme_service.get_account_by_thumbprint(db, jwk_thumbprint(jwk))
            if not existing:
                return _acme_error("unauthorized", "Registration is closed", 403)
        account = acme_service.get_or_create_account(db, jwk, payload.get("contact"), only_existing)
    except ValueError as e:
        return _acme_error(str(e), "Account does not exist", 400)

    base = _base_url(request)
    resp = JSONResponse(
        status_code=201,
        content={"status": account.status, "contact": account.contact or [], "orders": f"{base}/acme/account/{account.id}/orders"},
    )
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    resp.headers["Location"] = f"{base}/acme/account/{account.id}"
    return resp
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_jws_request.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/acme.py backend/tests/test_acme_jws_request.py
git commit -m "feat: add ACME JWS request parsing and new-account endpoint"
```

---

### Task 13: ACME router — new-order, authz, challenge endpoints

**Files:**
- Modify: `backend/app/routers/acme.py`
- Test: `backend/tests/test_acme_router_order.py`

**Interfaces:**
- Consumes: `parse_jws_request`, `acme_service`, `_resolve_ca_id`, `_base_url`.
- Produces endpoints: `POST /acme/new-order`, `POST /acme/order/{order_id}`, `POST /acme/authz/{authz_id}`, `POST /acme/challenge/{authz_id}/{challenge_type}`. Order/authz JSON shapes follow RFC (status, identifiers, authorizations URLs, challenges with `url`/`token`/`type`/`status`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_router_order.py`:

```python
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from app.services.acme_jws import b64url_encode


def _rsa_jwk(pub):
    n = pub.public_numbers()
    f = lambda v: b64url_encode(v.to_bytes((v.bit_length() + 7) // 8, "big"))
    return {"kty": "RSA", "n": f(n.n), "e": f(n.e)}


def _jws(key, url, nonce, payload, jwk=None, kid=None):
    protected = {"alg": "RS256", "nonce": nonce, "url": url}
    if kid:
        protected["kid"] = kid
    else:
        protected["jwk"] = jwk
    pb = b64url_encode(json.dumps(protected).encode())
    yb = b64url_encode(json.dumps(payload).encode()) if payload is not None else ""
    sig = key.sign(f"{pb}.{yb}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return {"protected": pb, "payload": yb, "signature": b64url_encode(sig)}


def _setup(client, db):
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value="ca-1"))
    db.commit()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk)
    r = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]
    return key, jwk, account_url


def test_new_order_creates_pending_order(client, db):
    key, jwk, account_url = _setup(client, db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "example.com"}]}, kid=account_url)
    resp = client.post("/acme/new-order", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert len(data["authorizations"]) == 1
    assert "finalize" in data


def test_authz_lists_challenges(client, db):
    key, jwk, account_url = _setup(client, db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "authz.com"}]}, kid=account_url)
    order = client.post("/acme/new-order", json=body, headers={"Content-Type": "application/jose+json"}).json()
    authz_url = order["authorizations"][0]
    authz_path = "/acme" + authz_url.split("/acme", 1)[1]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, authz_url, nonce, None, kid=account_url)
    resp = client.post(authz_path, json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["identifier"]["value"] == "authz.com"
    assert len(data["challenges"]) == 3
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_router_order.py -v`
Expected: FAIL — `/acme/new-order` 404.

- [ ] **Step 3: Add the order/authz/challenge endpoints**

In `backend/app/routers/acme.py`, add these endpoints. First add a serializer helper near the top (after `_directory_body`):

```python
def _order_json(request: Request, order, authzs) -> dict:
    base = _base_url(request)
    body = {
        "status": order.status,
        "expires": order.expires.isoformat() + "Z",
        "identifiers": order.identifiers,
        "authorizations": [f"{base}/acme/authz/{a.id}" for a in authzs],
        "finalize": f"{base}/acme/order/{order.id}/finalize",
    }
    if order.certificate_id:
        body["certificate"] = f"{base}/acme/order/{order.id}/cert"
    return body


def _authz_json(request: Request, authz) -> dict:
    base = _base_url(request)
    challenges = []
    for ch in authz.challenges:
        challenges.append({
            "type": ch["type"],
            "url": f"{base}/acme/challenge/{authz.id}/{ch['type']}",
            "token": ch["token"],
            "status": ch["status"],
        })
    return {
        "status": authz.status,
        "expires": authz.expires.isoformat() + "Z",
        "identifier": {"type": authz.identifier_type, "value": authz.identifier_value},
        "challenges": challenges,
    }
```

Then add the endpoints:

```python
@router.post("/new-order")
@router.post("/{ca_id}/new-order")
async def new_order(request: Request, db: Session = Depends(get_db), ca_id: str | None = None):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)

    resolved_ca = _resolve_ca_id(db, ca_id)
    if not resolved_ca:
        return _acme_error("unauthorized", "No CA configured for ACME", 403)

    identifiers = payload.get("identifiers", [])
    if not identifiers:
        return _acme_error("malformed", "No identifiers in order", 400)

    allowed = settings_service.get(db, "acme_allowed_domains")
    for ident in identifiers:
        if not acme_service.domain_allowed(allowed, ident["value"]):
            return _acme_error("rejectedIdentifier", f"Domain not allowed: {ident['value']}", 403)

    from app.models import AcmeAccount
    kid = protected["kid"]
    account_id = kid.rstrip("/").split("/")[-1]
    order = acme_service.create_order(db, account_id, resolved_ca, identifiers, None, None)
    authzs = acme_service.list_authorizations(db, order.id)
    base = _base_url(request)
    resp = JSONResponse(status_code=201, content=_order_json(request, order, authzs))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    resp.headers["Location"] = f"{base}/acme/order/{order.id}"
    return resp


@router.post("/order/{order_id}")
async def get_order_endpoint(order_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    order = acme_service.get_order(db, order_id)
    if not order:
        return _acme_error("malformed", "Order not found", 404)
    authzs = acme_service.list_authorizations(db, order.id)
    resp = JSONResponse(content=_order_json(request, order, authzs))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.post("/authz/{authz_id}")
async def get_authz_endpoint(authz_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    authz = acme_service.get_authorization(db, authz_id)
    if not authz:
        return _acme_error("malformed", "Authorization not found", 404)
    resp = JSONResponse(content=_authz_json(request, authz))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.post("/challenge/{authz_id}/{challenge_type}")
async def respond_challenge(authz_id: str, challenge_type: str, request: Request, db: Session = Depends(get_db)):
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    try:
        authz = acme_service.process_challenge(db, authz_id, challenge_type, jwk)
    except ValueError as e:
        return _acme_error(str(e), "Challenge processing failed", 400)
    base = _base_url(request)
    matching = next((c for c in authz.challenges if c["type"] == challenge_type), None)
    resp = JSONResponse(content={
        "type": challenge_type,
        "url": f"{base}/acme/challenge/{authz.id}/{challenge_type}",
        "token": matching["token"],
        "status": matching["status"],
    })
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_router_order.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/acme.py backend/tests/test_acme_router_order.py
git commit -m "feat: add ACME new-order, authz, and challenge endpoints"
```

---

### Task 14: ACME router — finalize and certificate download

**Files:**
- Modify: `backend/app/routers/acme.py`
- Test: `backend/tests/test_acme_router_finalize.py`

**Interfaces:**
- Consumes: `acme_service.finalize_order`, `acme_service.get_order_certificate_pem`, `b64url_decode`.
- Produces endpoints: `POST /acme/order/{order_id}/finalize`, `POST /acme/order/{order_id}/cert` (RFC allows POST-as-GET; we accept POST and return PEM with `Content-Type: application/pem-certificate-chain`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_router_finalize.py`:

```python
import json
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from app.services.acme_jws import b64url_encode


def _rsa_jwk(pub):
    n = pub.public_numbers()
    f = lambda v: b64url_encode(v.to_bytes((v.bit_length() + 7) // 8, "big"))
    return {"kty": "RSA", "n": f(n.n), "e": f(n.e)}


def _jws(key, url, nonce, payload, jwk=None, kid=None):
    protected = {"alg": "RS256", "nonce": nonce, "url": url}
    if kid:
        protected["kid"] = kid
    else:
        protected["jwk"] = jwk
    pb = b64url_encode(json.dumps(protected).encode())
    yb = b64url_encode(json.dumps(payload).encode()) if payload is not None else ""
    sig = key.sign(f"{pb}.{yb}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return {"protected": pb, "payload": yb, "signature": b64url_encode(sig)}


def _csr_der(domain):
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
           .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
           .sign(k, hashes.SHA256()))
    return csr.public_bytes(serialization.Encoding.DER)


def _make_ca(db):
    from app.routers.cas import ca_service
    from app.models import User, UserRole
    from app.services.auth_service import AuthService
    admin = User(username="acfin", email="acfin@t.com", password_hash=AuthService().hash_password("x"), role=UserRole.admin)
    db.add(admin); db.commit(); db.refresh(admin)
    return ca_service.create_root_ca(db, admin.id, {
        "name": "FinCA", "description": None, "subject": {"CN": "FinCA"},
        "key_algorithm": "RSA", "key_size": 2048, "validity_days": 3650,
        "max_path_length": None, "auto_approve": True, "crl_distribution_url": None, "ocsp_url": None,
    })


def test_full_order_to_certificate(client, db):
    ca = _make_ca(db)
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value=ca.id))
    db.commit()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk), headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "acme-e2e.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    order_id = order["finalize"].split("/order/")[1].split("/finalize")[0]
    authz_url = order["authorizations"][0]
    authz_id = authz_url.split("/authz/")[1]

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        client.post(f"/acme/challenge/{authz_id}/http-01", json=_jws(key, f"http://testserver/acme/challenge/{authz_id}/http-01", nonce, {}, kid=account_url), headers={"Content-Type": "application/jose+json"})

    csr_b64 = b64url_encode(_csr_der("acme-e2e.com"))
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    fin = client.post(f"/acme/order/{order_id}/finalize", json=_jws(key, f"http://testserver/acme/order/{order_id}/finalize", nonce, {"csr": csr_b64}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert fin.status_code == 200
    assert fin.json()["status"] == "valid"

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    cert = client.post(f"/acme/order/{order_id}/cert", json=_jws(key, f"http://testserver/acme/order/{order_id}/cert", nonce, None, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert cert.status_code == 200
    assert "BEGIN CERTIFICATE" in cert.text
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_router_finalize.py -v`
Expected: FAIL — finalize endpoint 404.

- [ ] **Step 3: Add finalize and cert endpoints**

In `backend/app/routers/acme.py`, add:

```python
@router.post("/order/{order_id}/finalize")
async def finalize(order_id: str, request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)

    csr_b64 = payload.get("csr")
    if not csr_b64:
        return _acme_error("badCSR", "Missing CSR", 400)
    try:
        csr_der = b64url_decode(csr_b64)
    except Exception:
        return _acme_error("badCSR", "Invalid CSR encoding", 400)

    try:
        order = acme_service.finalize_order(db, order_id, csr_der)
    except ValueError as e:
        return _acme_error(str(e), "Finalization failed", 400)

    authzs = acme_service.list_authorizations(db, order.id)
    resp = JSONResponse(content=_order_json(request, order, authzs))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    resp.headers["Location"] = f"{_base_url(request)}/acme/order/{order.id}"
    return resp


@router.post("/order/{order_id}/cert")
async def download_cert(order_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    try:
        pem = acme_service.get_order_certificate_pem(db, order_id)
    except ValueError as e:
        return _acme_error(str(e), "Certificate not available", 404)
    resp = Response(content=pem, media_type="application/pem-certificate-chain")
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_router_finalize.py -v`
Expected: PASS (1 test — the full end-to-end flow).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/acme.py backend/tests/test_acme_router_finalize.py
git commit -m "feat: add ACME finalize and certificate download endpoints"
```

---

### Task 15: ACME certificate revocation endpoint

**Files:**
- Modify: `backend/app/routers/acme.py`
- Test: `backend/tests/test_acme_revoke.py`

**Interfaces:**
- Consumes: `parse_jws_request`, `b64url_decode`, `CertificateService.revoke`, `acme_service.get_system_user_id`.
- Produces endpoint: `POST /acme/revoke-cert`. Payload carries `certificate` (base64url DER). Looks up the matching Certificate by comparing the DER's serial, revokes it.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acme_revoke.py`:

```python
import json
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from app.services.acme_jws import b64url_encode


def _rsa_jwk(pub):
    n = pub.public_numbers()
    f = lambda v: b64url_encode(v.to_bytes((v.bit_length() + 7) // 8, "big"))
    return {"kty": "RSA", "n": f(n.n), "e": f(n.e)}


def _jws(key, url, nonce, payload, jwk=None, kid=None):
    protected = {"alg": "RS256", "nonce": nonce, "url": url}
    if kid:
        protected["kid"] = kid
    else:
        protected["jwk"] = jwk
    pb = b64url_encode(json.dumps(protected).encode())
    yb = b64url_encode(json.dumps(payload).encode()) if payload is not None else ""
    sig = key.sign(f"{pb}.{yb}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return {"protected": pb, "payload": yb, "signature": b64url_encode(sig)}


def _csr_der(domain):
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
           .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
           .sign(k, hashes.SHA256()))
    return csr.public_bytes(serialization.Encoding.DER)


def _make_ca(db):
    from app.routers.cas import ca_service
    from app.models import User, UserRole
    from app.services.auth_service import AuthService
    admin = User(username="acrev", email="acrev@t.com", password_hash=AuthService().hash_password("x"), role=UserRole.admin)
    db.add(admin); db.commit(); db.refresh(admin)
    return ca_service.create_root_ca(db, admin.id, {
        "name": "RevCA", "description": None, "subject": {"CN": "RevCA"},
        "key_algorithm": "RSA", "key_size": 2048, "validity_days": 3650,
        "max_path_length": None, "auto_approve": True, "crl_distribution_url": None, "ocsp_url": None,
    })


def test_revoke_certificate(client, db):
    ca = _make_ca(db)
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value=ca.id))
    db.commit()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk), headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "revoke-me.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    order_id = order["finalize"].split("/order/")[1].split("/finalize")[0]
    authz_id = order["authorizations"][0].split("/authz/")[1]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        client.post(f"/acme/challenge/{authz_id}/http-01", json=_jws(key, f"http://testserver/acme/challenge/{authz_id}/http-01", nonce, {}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    client.post(f"/acme/order/{order_id}/finalize", json=_jws(key, f"http://testserver/acme/order/{order_id}/finalize", nonce, {"csr": b64url_encode(_csr_der("revoke-me.com"))}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    cert_pem = client.post(f"/acme/order/{order_id}/cert", json=_jws(key, f"http://testserver/acme/order/{order_id}/cert", nonce, None, kid=account_url), headers={"Content-Type": "application/jose+json"}).text

    leaf = cert_pem.split("-----END CERTIFICATE-----")[0] + "-----END CERTIFICATE-----\n"
    der = x509.load_pem_x509_certificate(leaf.encode()).public_bytes(serialization.Encoding.DER)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post("/acme/revoke-cert", json=_jws(key, "http://testserver/acme/revoke-cert", nonce, {"certificate": b64url_encode(der)}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_revoke.py -v`
Expected: FAIL — revoke-cert 404.

- [ ] **Step 3: Add revoke logic to AcmeService and the endpoint**

In `backend/app/services/acme_service.py`, add a method to `AcmeService`:

```python
    def revoke_certificate(self, db: Session, cert_der: bytes) -> None:
        cert = x509.load_der_x509_certificate(cert_der)
        serial_hex = format(cert.serial_number, "x")
        record = db.query(Certificate).filter(Certificate.serial_number == serial_hex).first()
        if not record:
            raise ValueError("malformed")
        from app.models import CertificateStatus
        if record.status != CertificateStatus.active:
            raise ValueError("alreadyRevoked")
        system_user_id = self.get_system_user_id(db)
        cert_service.revoke(db, system_user_id, record.id, "unspecified")
```

In `backend/app/routers/acme.py`, add:

```python
@router.post("/revoke-cert")
async def revoke_cert(request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    cert_b64 = payload.get("certificate")
    if not cert_b64:
        return _acme_error("malformed", "Missing certificate", 400)
    try:
        der = b64url_decode(cert_b64)
        acme_service.revoke_certificate(db, der)
    except ValueError as e:
        return _acme_error(str(e), "Revocation failed", 400)
    resp = Response(status_code=200)
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_acme_revoke.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/acme_service.py backend/app/routers/acme.py backend/tests/test_acme_revoke.py
git commit -m "feat: add ACME certificate revocation endpoint"
```

---

### Task 16: Nginx proxy route and full backend test run

**Files:**
- Modify: `proxy/nginx.conf.template`
- Test: full backend suite

**Interfaces:**
- Consumes: nothing new.
- Produces: `/acme` proxied to backend in production.

- [ ] **Step 1: Add the nginx location block**

In `proxy/nginx.conf.template`, add after the `location /mcp { ... }` block:

```nginx
    location /acme {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

- [ ] **Step 2: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -v`
Expected: All ACME tests pass; pre-existing `test_create_user` may still fail (known password-policy issue, unrelated). No new failures.

- [ ] **Step 3: Commit**

```bash
git add proxy/nginx.conf.template
git commit -m "feat: proxy /acme to backend in nginx"
```

---

### Task 17: Frontend Settings category and ACME docs tab

**Files:**
- Modify: `frontend/src/pages/Settings.jsx`
- Modify: `frontend/src/pages/Docs.jsx`

**Interfaces:**
- Consumes: existing `categoryLabels`/`categoryDescriptions` maps and the `Section`/`CodeBlock` doc components.
- Produces: ACME category renders on Settings; ACME documentation tab.

- [ ] **Step 1: Add the ACME settings category labels**

In `frontend/src/pages/Settings.jsx`, add to `categoryLabels` (after `mcp: 'MCP Server',`):

```javascript
  acme: 'ACME Server',
```

And to `categoryDescriptions` (after the `mcp:` line):

```javascript
  acme: 'ACME protocol server for automated clients (certbot, Caddy)',
```

- [ ] **Step 2: Build the frontend to confirm no syntax errors**

Run: `cd frontend && npx vite build --mode development 2>&1 | tail -3`
Expected: `✓ built in ...`. The ACME settings (including the `acme_default_ca_id` string field) render via the existing definition-driven `SettingField`. Note: string-type settings render as a text input — confirm the existing `SettingField` handles the `string` type; if it only handles `bool` and number, add a string branch.

- [ ] **Step 3: Verify SettingField handles string type**

Read `frontend/src/pages/Settings.jsx` `SettingField`. If it lacks a string branch (only `bool` + number), add before the final number `return`:

```javascript
  if (definition.type === 'string') {
    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
        <div className="flex-1 mr-4">
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{definition.label}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{definition.description}</div>
        </div>
        <input
          type="text"
          value={value || ''}
          onChange={(e) => onChange(settingKey, e.target.value)}
          className="w-64 px-3 py-1.5 rounded border text-sm bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-gray-500"
        />
      </div>
    )
  }
```

- [ ] **Step 4: Add the ACME documentation tab**

In `frontend/src/pages/Docs.jsx`, add a new `AcmeGuide` function component before the `tabs` array:

```javascript
function AcmeGuide() {
  return (
    <div>
      <H2>ACME Server</H2>
      <P>Certifactory includes an ACME (RFC 8555) server, letting automated clients like certbot and Caddy obtain certificates without manual steps. ACME is an additional feature — the web UI, REST API, and MCP server are unaffected.</P>

      <Section title="Enabling ACME" defaultOpen>
        <P>On the <strong>Settings</strong> page, under <strong>ACME Server</strong>:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>ACME Server Enabled</strong> — global on/off switch.</Li>
          <Li><strong>ACME Default CA</strong> — the CA used for the default <Code>/acme/directory</Code> endpoint.</Li>
          <Li><strong>ACME Open Registration</strong> — allow new clients to register accounts.</Li>
          <Li><strong>ACME Allowed Domains</strong> — restrict issuance to matching domains (e.g. <Code>*.example.com</Code>). Empty allows all.</Li>
        </ul>
      </Section>

      <Section title="Directory URLs">
        <P>Point your ACME client at one of these directory URLs:</P>
        <CodeBlock>{`# Default CA
https://your-server/acme/directory

# A specific CA by ID
https://your-server/acme/<ca_id>/directory`}</CodeBlock>
      </Section>

      <Section title="Using certbot">
        <P>Request a certificate with the HTTP-01 challenge:</P>
        <CodeBlock>{`certbot certonly \\
  --server https://your-server/acme/directory \\
  --standalone \\
  -d example.com -d www.example.com`}</CodeBlock>
      </Section>

      <Section title="Using Caddy">
        <P>In your Caddyfile, set the ACME CA globally:</P>
        <CodeBlock>{`{
  acme_ca https://your-server/acme/directory
}

example.com {
  respond "Hello"
}`}</CodeBlock>
      </Section>

      <Section title="Challenge Types">
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>HTTP-01</strong> — Certifactory fetches a token from <Code>http://domain/.well-known/acme-challenge/</Code>.</Li>
          <Li><strong>DNS-01</strong> — Certifactory checks a TXT record at <Code>_acme-challenge.domain</Code>. Required for wildcards.</Li>
          <Li><strong>TLS-ALPN-01</strong> — Certifactory connects on port 443 using the <Code>acme-tls/1</Code> protocol.</Li>
        </ul>
      </Section>
    </div>
  )
}
```

Then add it to the `tabs` array after the `mcp` entry:

```javascript
  { key: 'acme', label: 'ACME', content: <AcmeGuide /> },
```

- [ ] **Step 5: Build to confirm**

Run: `cd frontend && npx vite build --mode development 2>&1 | tail -3`
Expected: `✓ built`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Settings.jsx frontend/src/pages/Docs.jsx
git commit -m "feat: add ACME settings category and documentation tab"
```

---

### Task 18: End-to-end verification and push

**Files:** none new.

- [ ] **Step 1: Run the entire backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -v`
Expected: all ACME tests green; only the known pre-existing `test_create_user` failure (if still present) remains.

- [ ] **Step 2: Start the server and smoke-test the directory**

Run:
```bash
cd backend && lsof -ti:8099 | xargs kill -9 2>/dev/null; .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8099 > /tmp/acme_test.log 2>&1 &
sleep 4
curl -s -X PUT http://127.0.0.1:8099/api/v1/settings -H "Content-Type: application/json" -d '{}' >/dev/null 2>&1 || true
curl -s http://127.0.0.1:8099/acme/directory
```
Expected: a 403 problem+json (ACME disabled by default — confirms the endpoint is wired). Stop the server: `lsof -ti:8099 | xargs kill -9`.

- [ ] **Step 3: Push**

```bash
git push
```

Expected: all ACME commits pushed to origin.
