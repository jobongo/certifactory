# PKI Server Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend for a PKI certificate management server with full CA hierarchy management, certificate lifecycle, OCSP responder, and audit logging.

**Architecture:** Layered FastAPI application — routers handle HTTP, services contain business logic, crypto_service.py is the single interface to the `cryptography` library. SQLAlchemy ORM with Alembic migrations, SQLite by default (swappable to PostgreSQL via env var). APScheduler for background jobs (CRL regeneration, expiration checks).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, python-jose[cryptography], passlib[bcrypt], cryptography, APScheduler, pytest, httpx

---

## File Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app, CORS, router registration, scheduler startup
│   ├── config.py                        # Pydantic Settings (DATABASE_URL, PKI_MASTER_KEY, JWT settings)
│   ├── database.py                      # SQLAlchemy engine, SessionLocal, Base
│   ├── models/
│   │   ├── __init__.py                  # Re-exports all models
│   │   ├── user.py                      # User ORM model
│   │   ├── certificate_authority.py     # CA ORM model
│   │   ├── certificate.py              # Certificate ORM model
│   │   ├── crl.py                       # CRL ORM model
│   │   └── audit_log.py                # AuditLog ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                      # Login request/response, token schemas
│   │   ├── user.py                      # User CRUD schemas
│   │   ├── ca.py                        # CA create/update/response schemas
│   │   ├── certificate.py              # Cert request/response/download schemas
│   │   ├── crl.py                       # CRL response schemas
│   │   ├── audit.py                     # Audit log query/response schemas
│   │   └── dashboard.py                # Stats and expiring cert schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                      # /api/v1/auth/*
│   │   ├── users.py                     # /api/v1/users/*
│   │   ├── cas.py                       # /api/v1/cas/*
│   │   ├── certificates.py             # /api/v1/certificates/*
│   │   ├── crl.py                       # /api/v1/cas/{id}/crl/*
│   │   ├── ocsp.py                      # /api/v1/ocsp/{ca_id}
│   │   ├── audit.py                     # /api/v1/audit/*
│   │   └── dashboard.py                # /api/v1/dashboard/*
│   ├── services/
│   │   ├── __init__.py
│   │   ├── crypto_service.py           # All cryptography library operations
│   │   ├── encryption.py               # AES-256-GCM encrypt/decrypt for private keys
│   │   ├── auth_service.py             # JWT creation/validation, password hashing
│   │   ├── ca_service.py               # CA business logic
│   │   ├── certificate_service.py      # Certificate business logic
│   │   ├── crl_service.py              # CRL generation logic
│   │   ├── ocsp_service.py             # OCSP response building
│   │   └── audit_service.py            # Audit log writing/querying
│   ├── dependencies.py                  # FastAPI deps: get_db, get_current_user, require_role
│   └── scheduler/
│       ├── __init__.py
│       └── jobs.py                      # APScheduler job definitions
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Test DB, test client, fixtures
│   ├── test_crypto_service.py
│   ├── test_encryption.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_cas.py
│   ├── test_certificates.py
│   ├── test_crl.py
│   ├── test_ocsp.py
│   ├── test_audit.py
│   └── test_dashboard.py
└── requirements.txt
```

---

## Task 1: Project Setup & Configuration

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.31
alembic==1.13.1
pydantic[email]==2.7.4
pydantic-settings==2.3.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==42.0.8
apscheduler==3.10.4
python-multipart==0.0.9
httpx==0.27.0
pytest==8.2.2
pytest-asyncio==0.23.7
```

- [ ] **Step 2: Create app/__init__.py**

```python
```

Empty file.

- [ ] **Step 3: Create app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./pki.db"
    PKI_MASTER_KEY: str = "CHANGE-ME-IN-PRODUCTION-32-BYTES"
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEFAULT_CRL_REGEN_HOURS: int = 24
    EXPIRY_WARNING_DAYS: int = 30
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: Create app/database.py**

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 5: Create app/main.py (minimal)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="PKI Manager", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 6: Verify the server starts**

Run: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`

Expected: Server starts, `GET /health` returns `{"status": "ok"}`

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: backend project setup with FastAPI, config, and database"
```

---

## Task 2: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/certificate_authority.py`
- Create: `backend/app/models/certificate.py`
- Create: `backend/app/models/crl.py`
- Create: `backend/app/models/audit_log.py`

- [ ] **Step 1: Create models/user.py**

```python
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    requester = "requester"
    auditor = "auditor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.requester)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: Create models/certificate_authority.py**

```python
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CAType(str, enum.Enum):
    root = "root"
    intermediate = "intermediate"


class CAStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    expired = "expired"
    revoked = "revoked"


class KeyAlgorithm(str, enum.Enum):
    RSA = "RSA"
    EC = "EC"


class OCSPSigningMode(str, enum.Enum):
    ca_key = "ca_key"
    dedicated_cert = "dedicated_cert"


class CertificateAuthority(Base):
    __tablename__ = "certificate_authorities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[CAType] = mapped_column(Enum(CAType), nullable=False)
    status: Mapped[CAStatus] = mapped_column(Enum(CAStatus), default=CAStatus.active)
    parent_ca_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("certificate_authorities.id"), nullable=True
    )
    private_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    certificate_pem: Mapped[str] = mapped_column(Text, nullable=False)
    key_algorithm: Mapped[KeyAlgorithm] = mapped_column(Enum(KeyAlgorithm), nullable=False)
    key_size: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_dn: Mapped[str] = mapped_column(String(1024), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False)
    not_before: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    not_after: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    max_path_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    crl_regen_interval_hours: Mapped[int] = mapped_column(Integer, default=24)
    ocsp_signing_mode: Mapped[OCSPSigningMode] = mapped_column(
        Enum(OCSPSigningMode), default=OCSPSigningMode.ca_key
    )
    ocsp_signing_cert_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocsp_signing_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    crl_distribution_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ocsp_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    parent = relationship("CertificateAuthority", remote_side="CertificateAuthority.id", backref="children")
    creator = relationship("User", foreign_keys=[created_by])
```

- [ ] **Step 3: Create models/certificate.py**

```python
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database import Base
from app.models.certificate_authority import KeyAlgorithm


class CertificateStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    revoked = "revoked"
    expired = "expired"
    denied = "denied"


class CertificateType(str, enum.Enum):
    server = "server"
    client = "client"
    custom = "custom"


class RevocationReason(str, enum.Enum):
    key_compromise = "key_compromise"
    ca_compromise = "ca_compromise"
    affiliation_changed = "affiliation_changed"
    superseded = "superseded"
    cessation_of_operation = "cessation_of_operation"
    certificate_hold = "certificate_hold"
    unspecified = "unspecified"


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ca_id: Mapped[str] = mapped_column(String(36), ForeignKey("certificate_authorities.id"), nullable=False)
    status: Mapped[CertificateStatus] = mapped_column(Enum(CertificateStatus), default=CertificateStatus.pending)
    type: Mapped[CertificateType] = mapped_column(Enum(CertificateType), nullable=False)
    private_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    csr_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_algorithm: Mapped[KeyAlgorithm] = mapped_column(Enum(KeyAlgorithm), nullable=False)
    key_size: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_dn: Mapped[str] = mapped_column(String(1024), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False)
    san: Mapped[list | None] = mapped_column(JSON, nullable=True)
    not_before: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    not_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    key_usage: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extended_key_usage: Mapped[list | None] = mapped_column(JSON, nullable=True)
    custom_extensions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    revocation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revocation_reason: Mapped[RevocationReason | None] = mapped_column(Enum(RevocationReason), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    ca = relationship("CertificateAuthority", backref="certificates")
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])
```

- [ ] **Step 4: Create models/crl.py**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CertificateRevocationList(Base):
    __tablename__ = "certificate_revocation_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ca_id: Mapped[str] = mapped_column(String(36), ForeignKey("certificate_authorities.id"), nullable=False)
    crl_pem: Mapped[str] = mapped_column(Text, nullable=False)
    this_update: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    next_update: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    crl_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    ca = relationship("CertificateAuthority", backref="crls")
```

- [ ] **Step 5: Create models/audit_log.py**

```python
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database import Base


class AuditAction(str, enum.Enum):
    created_ca = "created_ca"
    issued_cert = "issued_cert"
    revoked_cert = "revoked_cert"
    approved_request = "approved_request"
    denied_request = "denied_request"
    login = "login"
    logout = "logout"
    config_change = "config_change"
    downloaded_cert = "downloaded_cert"
    created_user = "created_user"
    updated_user = "updated_user"
    generated_crl = "generated_crl"
    renewed_cert = "renewed_cert"
    submitted_csr = "submitted_csr"


class AuditResourceType(str, enum.Enum):
    ca = "ca"
    certificate = "certificate"
    user = "user"
    crl = "crl"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    resource_type: Mapped[AuditResourceType] = mapped_column(Enum(AuditResourceType), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
```

- [ ] **Step 6: Create models/__init__.py**

```python
from app.models.user import User, UserRole
from app.models.certificate_authority import (
    CertificateAuthority,
    CAType,
    CAStatus,
    KeyAlgorithm,
    OCSPSigningMode,
)
from app.models.certificate import (
    Certificate,
    CertificateStatus,
    CertificateType,
    RevocationReason,
)
from app.models.crl import CertificateRevocationList
from app.models.audit_log import AuditLog, AuditAction, AuditResourceType

__all__ = [
    "User",
    "UserRole",
    "CertificateAuthority",
    "CAType",
    "CAStatus",
    "KeyAlgorithm",
    "OCSPSigningMode",
    "Certificate",
    "CertificateStatus",
    "CertificateType",
    "RevocationReason",
    "CertificateRevocationList",
    "AuditLog",
    "AuditAction",
    "AuditResourceType",
]
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add SQLAlchemy ORM models for all tables"
```

---

## Task 3: Alembic Setup & Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (directory)

- [ ] **Step 1: Initialize Alembic**

Run: `cd backend && alembic init alembic`

- [ ] **Step 2: Update alembic.ini — set SQLite URL**

In `alembic.ini`, set:
```ini
sqlalchemy.url = sqlite:///./pki.db
```

- [ ] **Step 3: Update alembic/env.py to use app models and config**

Replace `alembic/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app.models import *  # noqa: F401,F403 — registers all models with Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial schema"`

Expected: A migration file is created in `alembic/versions/`

- [ ] **Step 5: Run the migration**

Run: `cd backend && alembic upgrade head`

Expected: All tables created in `pki.db`

- [ ] **Step 6: Verify tables exist**

Run: `cd backend && python -c "from app.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"`

Expected: `['alembic_version', 'audit_logs', 'certificate_authorities', 'certificate_revocation_lists', 'certificates', 'users']`

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/ backend/alembic.ini
git commit -m "feat: alembic setup with initial schema migration"
```

---

## Task 4: Encryption Service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/encryption.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_encryption.py`

- [ ] **Step 1: Create services/__init__.py**

```python
```

Empty file.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/__init__.py` (empty) and `backend/tests/test_encryption.py`:

```python
from app.services.encryption import encrypt_private_key, decrypt_private_key


def test_encrypt_decrypt_roundtrip():
    master_key = "test-master-key-that-is-32-bytes!"
    plaintext = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
    encrypted = encrypt_private_key(plaintext, master_key)
    assert encrypted != plaintext
    decrypted = decrypt_private_key(encrypted, master_key)
    assert decrypted == plaintext


def test_different_master_key_fails():
    master_key = "test-master-key-that-is-32-bytes!"
    wrong_key = "wrong-master-key-that-is-32-byt!"
    plaintext = "secret key data"
    encrypted = encrypt_private_key(plaintext, master_key)
    try:
        decrypt_private_key(encrypted, wrong_key)
        assert False, "Should have raised an exception"
    except Exception:
        pass


def test_encrypted_output_is_base64():
    import base64
    master_key = "test-master-key-that-is-32-bytes!"
    plaintext = "secret key data"
    encrypted = encrypt_private_key(plaintext, master_key)
    base64.b64decode(encrypted)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_encryption.py -v`

Expected: FAIL — `ImportError: cannot import name 'encrypt_private_key'`

- [ ] **Step 4: Implement encryption service**

```python
import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(master_key: str) -> bytes:
    return hashlib.sha256(master_key.encode()).digest()


def encrypt_private_key(plaintext: str, master_key: str) -> str:
    key = _derive_key(master_key)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_private_key(encrypted: str, master_key: str) -> str:
    key = _derive_key(master_key)
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_encryption.py -v`

Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: AES-256-GCM encryption service for private key storage"
```

---

## Task 5: Crypto Service

**Files:**
- Create: `backend/app/services/crypto_service.py`
- Create: `backend/tests/test_crypto_service.py`

- [ ] **Step 1: Write failing tests for key generation**

```python
import pytest
from app.services.crypto_service import CryptoService


@pytest.fixture
def crypto():
    return CryptoService()


class TestKeyGeneration:
    def test_generate_rsa_key(self, crypto):
        key_pem = crypto.generate_key("RSA", 2048)
        assert "-----BEGIN RSA PRIVATE KEY-----" in key_pem or "-----BEGIN PRIVATE KEY-----" in key_pem

    def test_generate_ec_key(self, crypto):
        key_pem = crypto.generate_key("EC", 256)
        assert "-----BEGIN EC PRIVATE KEY-----" in key_pem or "-----BEGIN PRIVATE KEY-----" in key_pem

    def test_invalid_algorithm_raises(self, crypto):
        with pytest.raises(ValueError):
            crypto.generate_key("DSA", 2048)


class TestRootCA:
    def test_create_root_ca(self, crypto):
        key_pem = crypto.generate_key("RSA", 2048)
        subject = {"CN": "Test Root CA", "O": "Test Org", "C": "US"}
        cert_pem = crypto.create_root_ca(key_pem, subject, 3650)
        assert "-----BEGIN CERTIFICATE-----" in cert_pem

    def test_root_ca_is_self_signed(self, crypto):
        from cryptography import x509

        key_pem = crypto.generate_key("RSA", 2048)
        subject = {"CN": "Test Root CA", "O": "Test Org", "C": "US"}
        cert_pem = crypto.create_root_ca(key_pem, subject, 3650)
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        assert cert.issuer == cert.subject


class TestIntermediateCA:
    def test_create_intermediate_ca(self, crypto):
        root_key = crypto.generate_key("RSA", 2048)
        root_subject = {"CN": "Root CA", "O": "Test", "C": "US"}
        root_cert = crypto.create_root_ca(root_key, root_subject, 3650)

        int_key = crypto.generate_key("RSA", 2048)
        int_subject = {"CN": "Intermediate CA", "O": "Test", "C": "US"}
        int_cert = crypto.create_intermediate_ca(int_key, int_subject, root_cert, root_key, 1825)
        assert "-----BEGIN CERTIFICATE-----" in int_cert

    def test_intermediate_signed_by_root(self, crypto):
        from cryptography import x509

        root_key = crypto.generate_key("RSA", 2048)
        root_subject = {"CN": "Root CA", "O": "Test", "C": "US"}
        root_cert_pem = crypto.create_root_ca(root_key, root_subject, 3650)

        int_key = crypto.generate_key("RSA", 2048)
        int_subject = {"CN": "Intermediate CA", "O": "Test", "C": "US"}
        int_cert_pem = crypto.create_intermediate_ca(int_key, int_subject, root_cert_pem, root_key, 1825)

        root_cert = x509.load_pem_x509_certificate(root_cert_pem.encode())
        int_cert = x509.load_pem_x509_certificate(int_cert_pem.encode())
        assert int_cert.issuer == root_cert.subject


class TestCSRAndSigning:
    def test_generate_and_sign_csr(self, crypto):
        ca_key = crypto.generate_key("RSA", 2048)
        ca_subject = {"CN": "Test CA", "O": "Test", "C": "US"}
        ca_cert = crypto.create_root_ca(ca_key, ca_subject, 3650)

        cert_key = crypto.generate_key("RSA", 2048)
        csr_pem = crypto.generate_csr(cert_key, {"CN": "test.example.com"}, [{"type": "DNS", "value": "test.example.com"}])
        assert "-----BEGIN CERTIFICATE REQUEST-----" in csr_pem

        cert_pem = crypto.sign_csr(csr_pem, ca_cert, ca_key, 365)
        assert "-----BEGIN CERTIFICATE-----" in cert_pem


class TestFormatConversion:
    def test_convert_to_der(self, crypto):
        ca_key = crypto.generate_key("RSA", 2048)
        ca_cert = crypto.create_root_ca(ca_key, {"CN": "Test CA", "O": "Test", "C": "US"}, 365)
        der_bytes = crypto.convert_format(ca_cert, None, "der")
        assert isinstance(der_bytes, bytes)
        assert b"-----BEGIN" not in der_bytes

    def test_convert_to_pkcs12(self, crypto):
        ca_key = crypto.generate_key("RSA", 2048)
        ca_cert = crypto.create_root_ca(ca_key, {"CN": "Test CA", "O": "Test", "C": "US"}, 365)
        p12_bytes = crypto.convert_format(ca_cert, ca_key, "pkcs12", passphrase="test123")
        assert isinstance(p12_bytes, bytes)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_crypto_service.py -v`

Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement CryptoService**

```python
import uuid
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_NAME_OID_MAP = {
    "CN": NameOID.COMMON_NAME,
    "O": NameOID.ORGANIZATION_NAME,
    "OU": NameOID.ORGANIZATIONAL_UNIT_NAME,
    "C": NameOID.COUNTRY_NAME,
    "ST": NameOID.STATE_OR_PROVINCE_NAME,
    "L": NameOID.LOCALITY_NAME,
}

_EC_CURVES = {
    256: ec.SECP256R1(),
    384: ec.SECP384R1(),
    521: ec.SECP521R1(),
}

_KEY_USAGE_MAP = {
    "digital_signature": "digital_signature",
    "key_encipherment": "key_encipherment",
    "data_encipherment": "data_encipherment",
    "key_agreement": "key_agreement",
    "key_cert_sign": "key_cert_sign",
    "crl_sign": "crl_sign",
    "content_commitment": "content_commitment",
}

_EKU_MAP = {
    "server_auth": ExtendedKeyUsageOID.SERVER_AUTH,
    "client_auth": ExtendedKeyUsageOID.CLIENT_AUTH,
    "code_signing": ExtendedKeyUsageOID.CODE_SIGNING,
    "email_protection": ExtendedKeyUsageOID.EMAIL_PROTECTION,
    "ocsp_signing": ExtendedKeyUsageOID.OCSP_SIGNING,
}


class CryptoService:
    def generate_key(self, algorithm: str, key_size: int) -> str:
        if algorithm == "RSA":
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        elif algorithm == "EC":
            curve = _EC_CURVES.get(key_size)
            if curve is None:
                raise ValueError(f"Unsupported EC curve size: {key_size}")
            private_key = ec.generate_private_key(curve)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    def _load_private_key(self, key_pem: str):
        return serialization.load_pem_private_key(key_pem.encode(), password=None)

    def _build_subject(self, subject: dict) -> x509.Name:
        attrs = []
        for key, value in subject.items():
            oid = _NAME_OID_MAP.get(key)
            if oid:
                attrs.append(x509.NameAttribute(oid, value))
        return x509.Name(attrs)

    def _build_san_extension(self, sans: list[dict]) -> x509.SubjectAlternativeName | None:
        if not sans:
            return None
        names = []
        for san in sans:
            san_type = san["type"]
            value = san["value"]
            if san_type == "DNS":
                names.append(x509.DNSName(value))
            elif san_type == "IP":
                import ipaddress
                names.append(x509.IPAddress(ipaddress.ip_address(value)))
            elif san_type == "Email":
                names.append(x509.RFC822Name(value))
            elif san_type == "URI":
                names.append(x509.UniformResourceIdentifier(value))
        return x509.SubjectAlternativeName(names) if names else None

    def _get_hash_algorithm(self, private_key) -> hashes.HashAlgorithm:
        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            return hashes.SHA256()
        return hashes.SHA256()

    def _next_serial(self) -> int:
        return int(uuid.uuid4().int >> 96)

    def create_root_ca(
        self,
        key_pem: str,
        subject: dict,
        validity_days: int,
        max_path_length: int | None = None,
        extensions: dict | None = None,
    ) -> str:
        private_key = self._load_private_key(key_pem)
        subject_name = self._build_subject(subject)
        now = datetime.now(timezone.utc)

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject_name)
            .issuer_name(subject_name)
            .public_key(private_key.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=True, path_length=max_path_length), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False)
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(private_key.public_key()), critical=False
            )
        )

        cert = builder.sign(private_key, self._get_hash_algorithm(private_key))
        return cert.public_bytes(serialization.Encoding.PEM).decode()

    def create_intermediate_ca(
        self,
        key_pem: str,
        subject: dict,
        ca_cert_pem: str,
        ca_key_pem: str,
        validity_days: int,
        max_path_length: int | None = 0,
        extensions: dict | None = None,
    ) -> str:
        private_key = self._load_private_key(key_pem)
        ca_key = self._load_private_key(ca_key_pem)
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        subject_name = self._build_subject(subject)
        now = datetime.now(timezone.utc)

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject_name)
            .issuer_name(ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=True, path_length=max_path_length), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False)
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
            )
        )

        cert = builder.sign(ca_key, self._get_hash_algorithm(ca_key))
        return cert.public_bytes(serialization.Encoding.PEM).decode()

    def generate_csr(self, key_pem: str, subject: dict, sans: list[dict] | None = None) -> str:
        private_key = self._load_private_key(key_pem)
        subject_name = self._build_subject(subject)

        builder = x509.CertificateSigningRequestBuilder().subject_name(subject_name)

        san_ext = self._build_san_extension(sans or [])
        if san_ext:
            builder = builder.add_extension(san_ext, critical=False)

        csr = builder.sign(private_key, self._get_hash_algorithm(private_key))
        return csr.public_bytes(serialization.Encoding.PEM).decode()

    def sign_csr(
        self,
        csr_pem: str,
        ca_cert_pem: str,
        ca_key_pem: str,
        validity_days: int,
        key_usage: list[str] | None = None,
        extended_key_usage: list[str] | None = None,
        custom_extensions: list[dict] | None = None,
    ) -> str:
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        ca_key = self._load_private_key(ca_key_pem)
        now = datetime.now(timezone.utc)

        builder = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(ca_cert.subject)
            .public_key(csr.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        )

        for ext in csr.extensions:
            builder = builder.add_extension(ext.value, critical=ext.critical)

        if key_usage:
            ku_kwargs = {k: False for k in ["digital_signature", "key_encipherment", "content_commitment", "data_encipherment", "key_agreement", "key_cert_sign", "crl_sign", "encipher_only", "decipher_only"]}
            for ku in key_usage:
                mapped = _KEY_USAGE_MAP.get(ku)
                if mapped and mapped in ku_kwargs:
                    ku_kwargs[mapped] = True
            builder = builder.add_extension(x509.KeyUsage(**ku_kwargs), critical=True)

        if extended_key_usage:
            eku_oids = [_EKU_MAP[e] for e in extended_key_usage if e in _EKU_MAP]
            if eku_oids:
                builder = builder.add_extension(x509.ExtendedKeyUsage(eku_oids), critical=False)

        builder = builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(csr.public_key()), critical=False
        )
        builder = builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )

        cert = builder.sign(ca_key, self._get_hash_algorithm(ca_key))
        return cert.public_bytes(serialization.Encoding.PEM).decode()

    def generate_crl(
        self,
        ca_cert_pem: str,
        ca_key_pem: str,
        revoked_certs: list[dict],
        next_update_days: int = 7,
        crl_number: int = 1,
    ) -> str:
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        ca_key = self._load_private_key(ca_key_pem)
        now = datetime.now(timezone.utc)

        builder = (
            x509.CertificateRevocationListBuilder()
            .issuer_name(ca_cert.subject)
            .last_update(now)
            .next_update(now + timedelta(days=next_update_days))
            .add_extension(x509.CRLNumber(crl_number), critical=False)
        )

        for entry in revoked_certs:
            revoked = (
                x509.RevokedCertificateBuilder()
                .serial_number(int(entry["serial_number"], 16))
                .revocation_date(entry["revocation_date"])
                .build()
            )
            builder = builder.add_revoked_certificate(revoked)

        crl = builder.sign(ca_key, self._get_hash_algorithm(ca_key))
        return crl.public_bytes(serialization.Encoding.PEM).decode()

    def build_ocsp_response(
        self,
        ca_cert_pem: str,
        signing_key_pem: str,
        signing_cert_pem: str | None,
        cert_pem: str,
        cert_status: str,
        revocation_time: datetime | None = None,
    ) -> bytes:
        from cryptography.x509 import ocsp

        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        signing_key = self._load_private_key(signing_key_pem)
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        responder_cert = x509.load_pem_x509_certificate(signing_cert_pem.encode()) if signing_cert_pem else ca_cert
        now = datetime.now(timezone.utc)

        if cert_status == "good":
            builder = ocsp.OCSPResponseBuilder().add_response(
                cert=cert,
                issuer=ca_cert,
                algorithm=hashes.SHA256(),
                cert_status=ocsp.OCSPCertStatus.GOOD,
                this_update=now,
                next_update=now + timedelta(hours=1),
                revocation_time=None,
                revocation_reason=None,
            )
        elif cert_status == "revoked":
            builder = ocsp.OCSPResponseBuilder().add_response(
                cert=cert,
                issuer=ca_cert,
                algorithm=hashes.SHA256(),
                cert_status=ocsp.OCSPCertStatus.REVOKED,
                this_update=now,
                next_update=now + timedelta(hours=1),
                revocation_time=revocation_time,
                revocation_reason=None,
            )
        else:
            return ocsp.OCSPResponseBuilder.build_unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED).public_bytes(serialization.Encoding.DER)

        builder = builder.responder_id(ocsp.OCSPResponderEncoding.HASH, responder_cert)
        response = builder.sign(signing_key, hashes.SHA256())
        return response.public_bytes(serialization.Encoding.DER)

    def convert_format(
        self,
        cert_pem: str,
        key_pem: str | None,
        fmt: str,
        passphrase: str | None = None,
    ) -> bytes:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())

        if fmt == "pem":
            return cert.public_bytes(serialization.Encoding.PEM)
        elif fmt == "der":
            return cert.public_bytes(serialization.Encoding.DER)
        elif fmt == "pkcs12":
            private_key = self._load_private_key(key_pem) if key_pem else None
            pw = passphrase.encode() if passphrase else None
            return serialization.pkcs12.serialize_key_and_certificates(
                name=None,
                key=private_key,
                cert=cert,
                cas=None,
                encryption_algorithm=(
                    serialization.BestAvailableEncryption(pw) if pw else serialization.NoEncryption()
                ),
            )
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def generate_ocsp_signing_cert(
        self, ca_cert_pem: str, ca_key_pem: str
    ) -> tuple[str, str]:
        key_pem = self.generate_key("RSA", 2048)
        private_key = self._load_private_key(key_pem)
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        ca_key = self._load_private_key(ca_key_pem)
        now = datetime.now(timezone.utc)

        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"OCSP Signing - {ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value}"),
        ])

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, key_encipherment=False, content_commitment=False,
                    data_encipherment=False, key_agreement=False, key_cert_sign=False,
                    crl_sign=False, encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.OCSP_SIGNING]), critical=True
            )
            .add_extension(x509.OCSPNoCheck(), critical=False)
        )

        cert = builder.sign(ca_key, hashes.SHA256())
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        return cert_pem, key_pem

    def parse_csr(self, csr_pem: str) -> dict:
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        subject = {}
        for attr in csr.subject:
            for key, oid in _NAME_OID_MAP.items():
                if attr.oid == oid:
                    subject[key] = attr.value
        sans = []
        try:
            san_ext = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            for name in san_ext.value:
                if isinstance(name, x509.DNSName):
                    sans.append({"type": "DNS", "value": name.value})
                elif isinstance(name, x509.IPAddress):
                    sans.append({"type": "IP", "value": str(name.value)})
                elif isinstance(name, x509.RFC822Name):
                    sans.append({"type": "Email", "value": name.value})
                elif isinstance(name, x509.UniformResourceIdentifier):
                    sans.append({"type": "URI", "value": name.value})
        except x509.ExtensionNotFound:
            pass
        return {"subject": subject, "sans": sans}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_crypto_service.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/crypto_service.py backend/tests/test_crypto_service.py
git commit -m "feat: crypto service with key gen, CA creation, CSR signing, CRL, OCSP, format conversion"
```

---

## Task 6: Auth Service & Dependencies

**Files:**
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.dependencies import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    from app.models import User, UserRole
    from app.services.auth_service import AuthService

    auth = AuthService()
    user = User(
        username="admin",
        email="admin@test.com",
        password_hash=auth.hash_password("admin123"),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    from app.services.auth_service import AuthService

    auth = AuthService()
    return auth.create_access_token(admin_user.id, admin_user.role.value)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
```

Create `backend/tests/test_auth.py`:

```python
def test_login_success(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_me_endpoint(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_me_no_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_auth.py -v`

Expected: FAIL — import errors

- [ ] **Step 3: Implement auth_service.py**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def create_access_token(self, user_id: str, role: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(self, user_id: str, role: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {"sub": user_id, "role": role, "exp": expire, "type": "refresh"}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def decode_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            return None
```

- [ ] **Step 4: Implement dependencies.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, UserRole
from app.services.auth_service import AuthService

security = HTTPBearer()
auth_service = AuthService()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = auth_service.decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*roles: UserRole):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker
```

- [ ] **Step 5: Create auth schemas**

Create `backend/app/schemas/__init__.py` (empty) and `backend/app/schemas/auth.py`:

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 6: Create auth router**

Create `backend/app/routers/__init__.py` (empty) and `backend/app/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
auth_service = AuthService()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not auth_service.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    return TokenResponse(
        access_token=auth_service.create_access_token(user.id, user.role.value),
        refresh_token=auth_service.create_refresh_token(user.id, user.role.value),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out"}


@router.put("/me/password")
def change_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not auth_service.verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = auth_service.hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated"}
```

Add `PasswordChange` to the auth schemas:

```python
class PasswordChange(BaseModel):
    current_password: str
    new_password: str
```

And import it in the auth router:

```python
from app.schemas.auth import LoginRequest, PasswordChange, TokenResponse, UserResponse
```

- [ ] **Step 7: Register auth router in main.py**

Update `backend/app/main.py` — add after the CORS middleware:

```python
from app.routers import auth

app.include_router(auth.router)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`

Expected: All 4 tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/dependencies.py backend/app/schemas/ backend/app/routers/ backend/tests/
git commit -m "feat: auth service with JWT login, token validation, and RBAC dependencies"
```

---

## Task 7: User Management Router

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/routers/users.py`
- Create: `backend/tests/test_users.py`

- [ ] **Step 1: Write failing tests**

```python
def test_create_user(client, admin_headers):
    response = client.post(
        "/api/v1/users",
        json={"username": "operator1", "email": "op@test.com", "password": "pass123", "role": "operator"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["username"] == "operator1"
    assert response.json()["role"] == "operator"


def test_list_users(client, admin_headers, admin_user):
    response = client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_get_user(client, admin_headers, admin_user):
    response = client.get(f"/api/v1/users/{admin_user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_update_user(client, admin_headers, admin_user):
    response = client.put(
        f"/api/v1/users/{admin_user.id}",
        json={"role": "operator"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "operator"


def test_non_admin_cannot_create_user(client, db):
    from app.models import User, UserRole
    from app.services.auth_service import AuthService

    auth = AuthService()
    user = User(
        username="requester1",
        email="req@test.com",
        password_hash=auth.hash_password("pass123"),
        role=UserRole.requester,
    )
    db.add(user)
    db.commit()
    token = auth.create_access_token(user.id, user.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/users",
        json={"username": "newuser", "email": "new@test.com", "password": "pass123", "role": "requester"},
        headers=headers,
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_users.py -v`

Expected: FAIL

- [ ] **Step 3: Create user schemas**

```python
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "requester"


class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    per_page: int
```

- [ ] **Step 4: Create users router**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/users", tags=["users"])
auth_service = AuthService()


@router.get("/", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    total = db.query(User).count()
    users = db.query(User).offset((page - 1) * per_page).limit(per_page).all()
    return UserListResponse(items=users, total=total, page=page, per_page=per_page)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    if db.query(User).filter((User.username == body.username) | (User.email == body.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    user = User(
        username=body.username,
        email=body.email,
        password_hash=auth_service.hash_password(body.password),
        role=UserRole(body.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.username is not None:
        user.username = body.username
    if body.email is not None:
        user.email = body.email
    if body.role is not None:
        user.role = UserRole(body.role)
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
```

- [ ] **Step 5: Register users router in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import auth, users

app.include_router(auth.router)
app.include_router(users.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_users.py -v`

Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/user.py backend/app/routers/users.py backend/tests/test_users.py backend/app/main.py
git commit -m "feat: user management CRUD with admin-only access control"
```

---

## Task 8: Audit Service

**Files:**
- Create: `backend/app/services/audit_service.py`
- Create: `backend/tests/test_audit.py`

- [ ] **Step 1: Write failing test**

```python
from app.models import AuditAction, AuditResourceType


def test_audit_log_created_on_login(client, admin_user):
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    response = client.get("/api/v1/audit/logs", headers=_get_admin_headers(client))
    assert response.status_code == 200
    logs = response.json()["items"]
    assert any(log["action"] == "login" for log in logs)


def _get_admin_headers(client):
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_audit.py -v`

Expected: FAIL

- [ ] **Step 3: Implement audit_service.py**

```python
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog, AuditResourceType


class AuditService:
    def log(
        self,
        db: Session,
        user_id: str,
        action: AuditAction,
        resource_type: AuditResourceType,
        resource_id: str,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
```

- [ ] **Step 4: Create audit schemas and router**

Create `backend/app/schemas/audit.py`:

```python
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    details: dict | None
    ip_address: str | None
    created_at: str

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    per_page: int
```

Create `backend/app/routers/audit.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import AuditLog, AuditAction, AuditResourceType, User, UserRole
from app.schemas.audit import AuditLogListResponse

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/logs", response_model=AuditLogListResponse)
def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    action: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.auditor, UserRole.operator)),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == AuditAction(action))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == AuditResourceType(resource_type))
    total = query.count()
    items = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return AuditLogListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/logs/export")
def export_audit_logs(
    action: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.auditor)),
):
    import csv
    import io
    from fastapi.responses import StreamingResponse

    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == AuditAction(action))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == AuditResourceType(resource_type))
    logs = query.order_by(AuditLog.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "action", "resource_type", "resource_id", "ip_address", "created_at"])
    for log in logs:
        writer.writerow([log.id, log.user_id, log.action.value, log.resource_type.value, log.resource_id, log.ip_address, log.created_at])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
```

- [ ] **Step 5: Add audit logging to auth login and register router**

Update `backend/app/routers/auth.py` login endpoint to call audit service after successful login:

```python
from app.services.audit_service import AuditService
from app.models import AuditAction, AuditResourceType

audit_service = AuditService()

# Inside the login function, after creating tokens:
audit_service.log(db, user.id, AuditAction.login, AuditResourceType.user, user.id)
```

Register audit router in `main.py`:

```python
from app.routers import auth, users, audit

app.include_router(audit.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_audit.py -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/audit_service.py backend/app/schemas/audit.py backend/app/routers/audit.py backend/tests/test_audit.py backend/app/routers/auth.py backend/app/main.py
git commit -m "feat: audit service and router with login event logging"
```

---

## Task 9: CA Management Service & Router

**Files:**
- Create: `backend/app/services/ca_service.py`
- Create: `backend/app/schemas/ca.py`
- Create: `backend/app/routers/cas.py`
- Create: `backend/tests/test_cas.py`

- [ ] **Step 1: Write failing tests**

```python
def test_create_root_ca(client, admin_headers):
    response = client.post(
        "/api/v1/cas",
        json={
            "name": "Test Root CA",
            "subject": {"CN": "Test Root CA", "O": "TestOrg", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Root CA"
    assert data["type"] == "root"
    assert data["status"] == "active"


def test_create_intermediate_ca(client, admin_headers):
    root = client.post(
        "/api/v1/cas",
        json={
            "name": "Root CA",
            "subject": {"CN": "Root CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    ).json()

    response = client.post(
        f"/api/v1/cas/{root['id']}/intermediate",
        json={
            "name": "Intermediate CA",
            "subject": {"CN": "Intermediate CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 1825,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "intermediate"
    assert data["parent_ca_id"] == root["id"]


def test_list_cas(client, admin_headers):
    client.post(
        "/api/v1/cas",
        json={
            "name": "CA1",
            "subject": {"CN": "CA1", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    )
    response = client.get("/api/v1/cas", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_get_ca_tree(client, admin_headers):
    root = client.post(
        "/api/v1/cas",
        json={
            "name": "Root",
            "subject": {"CN": "Root", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/cas/{root['id']}/intermediate",
        json={
            "name": "Child",
            "subject": {"CN": "Child", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 1825,
        },
        headers=admin_headers,
    )
    response = client.get("/api/v1/cas/tree", headers=admin_headers)
    assert response.status_code == 200
    tree = response.json()
    assert len(tree) >= 1
    assert len(tree[0]["children"]) >= 1


def test_disable_ca(client, admin_headers):
    ca = client.post(
        "/api/v1/cas",
        json={
            "name": "DisableMe",
            "subject": {"CN": "DisableMe", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    ).json()
    response = client.post(f"/api/v1/cas/{ca['id']}/disable", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_cas.py -v`

Expected: FAIL

- [ ] **Step 3: Create CA schemas**

`backend/app/schemas/ca.py`:

```python
from pydantic import BaseModel


class SubjectDN(BaseModel):
    CN: str
    O: str | None = None
    OU: str | None = None
    C: str | None = None
    ST: str | None = None
    L: str | None = None


class CACreate(BaseModel):
    name: str
    description: str | None = None
    subject: SubjectDN
    key_algorithm: str = "RSA"
    key_size: int = 2048
    validity_days: int = 3650
    max_path_length: int | None = None
    auto_approve: bool = False
    crl_distribution_url: str | None = None
    ocsp_url: str | None = None


class CAUpdate(BaseModel):
    description: str | None = None
    auto_approve: bool | None = None
    ocsp_signing_mode: str | None = None
    crl_distribution_url: str | None = None
    ocsp_url: str | None = None
    crl_regen_interval_hours: int | None = None


class CAResponse(BaseModel):
    id: str
    name: str
    description: str | None
    type: str
    status: str
    parent_ca_id: str | None
    certificate_pem: str
    key_algorithm: str
    key_size: int
    subject_dn: str
    serial_number: str
    not_before: str
    not_after: str
    max_path_length: int | None
    auto_approve: bool
    crl_regen_interval_hours: int
    ocsp_signing_mode: str
    crl_distribution_url: str | None
    ocsp_url: str | None
    created_by: str
    created_at: str

    model_config = {"from_attributes": True}


class CATreeNode(BaseModel):
    id: str
    name: str
    type: str
    status: str
    subject_dn: str
    not_after: str
    children: list["CATreeNode"] = []


class CAListResponse(BaseModel):
    items: list[CAResponse]
    total: int
    page: int
    per_page: int
```

- [ ] **Step 4: Implement ca_service.py**

```python
from cryptography import x509

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AuditAction,
    AuditResourceType,
    CAStatus,
    CAType,
    CertificateAuthority,
    KeyAlgorithm,
    OCSPSigningMode,
)
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService
from app.services.encryption import encrypt_private_key

crypto = CryptoService()
audit = AuditService()


class CAService:
    def create_root_ca(self, db: Session, user_id: str, data: dict) -> CertificateAuthority:
        key_pem = crypto.generate_key(data["key_algorithm"], data["key_size"])
        subject = data["subject"]
        cert_pem = crypto.create_root_ca(
            key_pem, subject, data["validity_days"], max_path_length=data.get("max_path_length")
        )
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        subject_dn = cert.subject.rfc4514_string()

        ca = CertificateAuthority(
            name=data["name"],
            description=data.get("description"),
            type=CAType.root,
            private_key_encrypted=encrypt_private_key(key_pem, settings.PKI_MASTER_KEY),
            certificate_pem=cert_pem,
            key_algorithm=KeyAlgorithm(data["key_algorithm"]),
            key_size=data["key_size"],
            subject_dn=subject_dn,
            serial_number=format(cert.serial_number, "x"),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            max_path_length=data.get("max_path_length"),
            auto_approve=data.get("auto_approve", False),
            crl_distribution_url=data.get("crl_distribution_url"),
            ocsp_url=data.get("ocsp_url"),
            created_by=user_id,
        )
        db.add(ca)
        db.commit()
        db.refresh(ca)
        audit.log(db, user_id, AuditAction.created_ca, AuditResourceType.ca, ca.id, {"name": ca.name})
        return ca

    def create_intermediate_ca(
        self, db: Session, user_id: str, parent_ca_id: str, data: dict
    ) -> CertificateAuthority:
        parent = db.query(CertificateAuthority).filter(CertificateAuthority.id == parent_ca_id).first()
        if not parent:
            raise ValueError("Parent CA not found")
        if parent.status != CAStatus.active:
            raise ValueError("Parent CA is not active")

        from app.services.encryption import decrypt_private_key

        parent_key = decrypt_private_key(parent.private_key_encrypted, settings.PKI_MASTER_KEY)

        key_pem = crypto.generate_key(data["key_algorithm"], data["key_size"])
        subject = data["subject"]
        cert_pem = crypto.create_intermediate_ca(
            key_pem, subject, parent.certificate_pem, parent_key, data["validity_days"],
            max_path_length=data.get("max_path_length", 0),
        )
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        subject_dn = cert.subject.rfc4514_string()

        ca = CertificateAuthority(
            name=data["name"],
            description=data.get("description"),
            type=CAType.intermediate,
            parent_ca_id=parent_ca_id,
            private_key_encrypted=encrypt_private_key(key_pem, settings.PKI_MASTER_KEY),
            certificate_pem=cert_pem,
            key_algorithm=KeyAlgorithm(data["key_algorithm"]),
            key_size=data["key_size"],
            subject_dn=subject_dn,
            serial_number=format(cert.serial_number, "x"),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            max_path_length=data.get("max_path_length", 0),
            auto_approve=data.get("auto_approve", False),
            crl_distribution_url=data.get("crl_distribution_url"),
            ocsp_url=data.get("ocsp_url"),
            created_by=user_id,
        )
        db.add(ca)
        db.commit()
        db.refresh(ca)
        audit.log(db, user_id, AuditAction.created_ca, AuditResourceType.ca, ca.id, {"name": ca.name, "parent": parent.name})
        return ca

    def get_ca_tree(self, db: Session) -> list[dict]:
        cas = db.query(CertificateAuthority).all()
        ca_map = {ca.id: ca for ca in cas}
        roots = []

        def build_node(ca):
            children_cas = [c for c in cas if c.parent_ca_id == ca.id]
            return {
                "id": ca.id,
                "name": ca.name,
                "type": ca.type.value,
                "status": ca.status.value,
                "subject_dn": ca.subject_dn,
                "not_after": ca.not_after.isoformat() if ca.not_after else None,
                "children": [build_node(c) for c in children_cas],
            }

        for ca in cas:
            if ca.parent_ca_id is None:
                roots.append(build_node(ca))
        return roots

    def get_chain(self, db: Session, ca_id: str) -> list[str]:
        chain = []
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
        while ca:
            chain.append(ca.certificate_pem)
            ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca.parent_ca_id).first() if ca.parent_ca_id else None
        return chain
```

- [ ] **Step 5: Create CAs router**

`backend/app/routers/cas.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import CAStatus, CertificateAuthority, User, UserRole
from app.schemas.ca import CACreate, CAListResponse, CAResponse, CATreeNode, CAUpdate
from app.services.ca_service import CAService

router = APIRouter(prefix="/api/v1/cas", tags=["certificate-authorities"])
ca_service = CAService()


@router.get("/", response_model=CAListResponse)
def list_cas(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    total = db.query(CertificateAuthority).count()
    items = db.query(CertificateAuthority).offset((page - 1) * per_page).limit(per_page).all()
    return CAListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/tree", response_model=list[CATreeNode])
def get_ca_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    return ca_service.get_ca_tree(db)


@router.post("/", response_model=CAResponse, status_code=status.HTTP_201_CREATED)
def create_root_ca(
    body: CACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    data = body.model_dump()
    data["subject"] = body.subject.model_dump(exclude_none=True)
    ca = ca_service.create_root_ca(db, current_user.id, data)
    return ca


@router.get("/{ca_id}", response_model=CAResponse)
def get_ca(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    return ca


@router.put("/{ca_id}", response_model=CAResponse)
def update_ca(
    ca_id: str,
    body: CAUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(ca, key, value)
    db.commit()
    db.refresh(ca)
    return ca


@router.post("/{ca_id}/intermediate", response_model=CAResponse, status_code=status.HTTP_201_CREATED)
def create_intermediate_ca(
    ca_id: str,
    body: CACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    data = body.model_dump()
    data["subject"] = body.subject.model_dump(exclude_none=True)
    try:
        ca = ca_service.create_intermediate_ca(db, current_user.id, ca_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ca


@router.get("/{ca_id}/chain")
def get_ca_chain(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    chain = ca_service.get_chain(db, ca_id)
    if not chain:
        raise HTTPException(status_code=404, detail="CA not found")
    return {"chain": chain}


@router.post("/{ca_id}/disable", response_model=CAResponse)
def disable_ca(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    ca.status = CAStatus.disabled
    db.commit()
    db.refresh(ca)
    return ca


@router.post("/{ca_id}/enable", response_model=CAResponse)
def enable_ca(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    ca.status = CAStatus.active
    db.commit()
    db.refresh(ca)
    return ca
```

- [ ] **Step 6: Register CAs router in main.py**

```python
from app.routers import auth, users, audit, cas

app.include_router(cas.router)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_cas.py -v`

Expected: All 5 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/ca_service.py backend/app/schemas/ca.py backend/app/routers/cas.py backend/tests/test_cas.py backend/app/main.py
git commit -m "feat: CA management with root/intermediate creation, tree view, and enable/disable"
```

---

## Task 10: Certificate Management Service & Router

**Files:**
- Create: `backend/app/services/certificate_service.py`
- Create: `backend/app/schemas/certificate.py`
- Create: `backend/app/routers/certificates.py`
- Create: `backend/tests/test_certificates.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest


@pytest.fixture
def root_ca(client, admin_headers):
    return client.post(
        "/api/v1/cas",
        json={
            "name": "Test CA",
            "subject": {"CN": "Test CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
            "auto_approve": True,
        },
        headers=admin_headers,
    ).json()


@pytest.fixture
def approval_ca(client, admin_headers):
    return client.post(
        "/api/v1/cas",
        json={
            "name": "Approval CA",
            "subject": {"CN": "Approval CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
            "auto_approve": False,
        },
        headers=admin_headers,
    ).json()


def test_issue_certificate_auto_approve(client, admin_headers, root_ca):
    response = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": root_ca["id"],
            "subject": {"CN": "test.example.com"},
            "san": [{"type": "DNS", "value": "test.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "active"
    assert data["certificate_pem"] is not None


def test_certificate_pending_approval(client, admin_headers, approval_ca):
    response = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": approval_ca["id"],
            "subject": {"CN": "pending.example.com"},
            "san": [{"type": "DNS", "value": "pending.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_approve_certificate(client, admin_headers, approval_ca):
    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": approval_ca["id"],
            "subject": {"CN": "approve.example.com"},
            "san": [{"type": "DNS", "value": "approve.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    response = client.post(f"/api/v1/certificates/{cert['id']}/approve", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["certificate_pem"] is not None


def test_revoke_certificate(client, admin_headers, root_ca):
    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": root_ca["id"],
            "subject": {"CN": "revoke.example.com"},
            "san": [{"type": "DNS", "value": "revoke.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    response = client.post(
        f"/api/v1/certificates/{cert['id']}/revoke",
        json={"reason": "key_compromise"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"


def test_download_pem(client, admin_headers, root_ca):
    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": root_ca["id"],
            "subject": {"CN": "dl.example.com"},
            "san": [{"type": "DNS", "value": "dl.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    response = client.get(f"/api/v1/certificates/{cert['id']}/download?format=pem", headers=admin_headers)
    assert response.status_code == 200


def test_submit_csr(client, admin_headers, root_ca):
    from app.services.crypto_service import CryptoService

    crypto = CryptoService()
    key = crypto.generate_key("RSA", 2048)
    csr = crypto.generate_csr(key, {"CN": "csr.example.com"}, [{"type": "DNS", "value": "csr.example.com"}])
    response = client.post(
        "/api/v1/certificates/csr",
        json={"ca_id": root_ca["id"], "csr_pem": csr, "type": "server", "validity_days": 365},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "active"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_certificates.py -v`

Expected: FAIL

- [ ] **Step 3: Create certificate schemas**

`backend/app/schemas/certificate.py`:

```python
from pydantic import BaseModel

from app.schemas.ca import SubjectDN


class SANEntry(BaseModel):
    type: str
    value: str


class CertificateCreate(BaseModel):
    ca_id: str
    subject: SubjectDN
    san: list[SANEntry] | None = None
    type: str = "server"
    key_algorithm: str = "RSA"
    key_size: int = 2048
    validity_days: int = 365
    key_usage: list[str] | None = None
    extended_key_usage: list[str] | None = None
    custom_extensions: list[dict] | None = None


class CSRSubmit(BaseModel):
    ca_id: str
    csr_pem: str
    type: str = "server"
    validity_days: int = 365
    key_usage: list[str] | None = None
    extended_key_usage: list[str] | None = None


class CertificateRevoke(BaseModel):
    reason: str = "unspecified"


class CertificateResponse(BaseModel):
    id: str
    ca_id: str
    status: str
    type: str
    certificate_pem: str | None
    csr_pem: str | None
    key_algorithm: str
    key_size: int
    subject_dn: str
    serial_number: str
    san: list | None
    not_before: str | None
    not_after: str | None
    key_usage: list | None
    extended_key_usage: list | None
    revocation_date: str | None
    revocation_reason: str | None
    requested_by: str
    approved_by: str | None
    created_at: str

    model_config = {"from_attributes": True}


class CertificateListResponse(BaseModel):
    items: list[CertificateResponse]
    total: int
    page: int
    per_page: int
```

- [ ] **Step 4: Implement certificate_service.py**

```python
from datetime import datetime, timezone

from cryptography import x509
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AuditAction,
    AuditResourceType,
    CAStatus,
    Certificate,
    CertificateAuthority,
    CertificateStatus,
    CertificateType,
    KeyAlgorithm,
    RevocationReason,
)
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService
from app.services.encryption import decrypt_private_key, encrypt_private_key

crypto = CryptoService()
audit = AuditService()


class CertificateService:
    def _get_next_serial(self, db: Session, ca_id: str) -> str:
        count = db.query(Certificate).filter(Certificate.ca_id == ca_id).count()
        return format(count + 1, "x")

    def request_certificate(self, db: Session, user_id: str, data: dict) -> Certificate:
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == data["ca_id"]).first()
        if not ca:
            raise ValueError("CA not found")
        if ca.status != CAStatus.active:
            raise ValueError("CA is not active")

        key_pem = crypto.generate_key(data["key_algorithm"], data["key_size"])
        subject = data["subject"]
        sans = data.get("san", [])
        csr_pem = crypto.generate_csr(key_pem, subject, [s if isinstance(s, dict) else s.model_dump() for s in sans])

        serial = self._get_next_serial(db, ca.id)

        cert_record = Certificate(
            ca_id=ca.id,
            type=CertificateType(data["type"]),
            private_key_encrypted=encrypt_private_key(key_pem, settings.PKI_MASTER_KEY),
            csr_pem=csr_pem,
            key_algorithm=KeyAlgorithm(data["key_algorithm"]),
            key_size=data["key_size"],
            subject_dn=", ".join(f"{k}={v}" for k, v in subject.items()),
            serial_number=serial,
            san=[s if isinstance(s, dict) else s for s in sans],
            key_usage=data.get("key_usage"),
            extended_key_usage=data.get("extended_key_usage"),
            custom_extensions=data.get("custom_extensions"),
            requested_by=user_id,
        )

        if ca.auto_approve:
            self._sign_certificate(cert_record, ca, key_pem, data.get("validity_days", 365), user_id)

        db.add(cert_record)
        db.commit()
        db.refresh(cert_record)
        audit.log(db, user_id, AuditAction.issued_cert if cert_record.status == CertificateStatus.active else AuditAction.submitted_csr, AuditResourceType.certificate, cert_record.id)
        return cert_record

    def submit_csr(self, db: Session, user_id: str, data: dict) -> Certificate:
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == data["ca_id"]).first()
        if not ca:
            raise ValueError("CA not found")
        if ca.status != CAStatus.active:
            raise ValueError("CA is not active")

        csr_info = crypto.parse_csr(data["csr_pem"])
        serial = self._get_next_serial(db, ca.id)

        cert_record = Certificate(
            ca_id=ca.id,
            type=CertificateType(data["type"]),
            csr_pem=data["csr_pem"],
            key_algorithm=KeyAlgorithm.RSA,
            key_size=0,
            subject_dn=", ".join(f"{k}={v}" for k, v in csr_info["subject"].items()),
            serial_number=serial,
            san=csr_info["sans"],
            key_usage=data.get("key_usage"),
            extended_key_usage=data.get("extended_key_usage"),
            requested_by=user_id,
        )

        if ca.auto_approve:
            ca_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)
            cert_pem = crypto.sign_csr(
                data["csr_pem"], ca.certificate_pem, ca_key, data.get("validity_days", 365),
                key_usage=data.get("key_usage"), extended_key_usage=data.get("extended_key_usage"),
            )
            parsed = x509.load_pem_x509_certificate(cert_pem.encode())
            cert_record.certificate_pem = cert_pem
            cert_record.status = CertificateStatus.active
            cert_record.serial_number = format(parsed.serial_number, "x")
            cert_record.not_before = parsed.not_valid_before_utc
            cert_record.not_after = parsed.not_valid_after_utc
            cert_record.approved_by = user_id

        db.add(cert_record)
        db.commit()
        db.refresh(cert_record)
        audit.log(db, user_id, AuditAction.submitted_csr, AuditResourceType.certificate, cert_record.id)
        return cert_record

    def _sign_certificate(self, cert_record: Certificate, ca: CertificateAuthority, key_pem: str, validity_days: int, approver_id: str):
        ca_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)
        cert_pem = crypto.sign_csr(
            cert_record.csr_pem, ca.certificate_pem, ca_key, validity_days,
            key_usage=cert_record.key_usage, extended_key_usage=cert_record.extended_key_usage,
        )
        parsed = x509.load_pem_x509_certificate(cert_pem.encode())
        cert_record.certificate_pem = cert_pem
        cert_record.status = CertificateStatus.active
        cert_record.serial_number = format(parsed.serial_number, "x")
        cert_record.not_before = parsed.not_valid_before_utc
        cert_record.not_after = parsed.not_valid_after_utc
        cert_record.approved_by = approver_id

    def approve(self, db: Session, user_id: str, cert_id: str) -> Certificate:
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if cert.status != CertificateStatus.pending:
            raise ValueError("Certificate is not pending")
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == cert.ca_id).first()

        if cert.private_key_encrypted:
            key_pem = decrypt_private_key(cert.private_key_encrypted, settings.PKI_MASTER_KEY)
        else:
            key_pem = None

        ca_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)
        cert_pem = crypto.sign_csr(
            cert.csr_pem, ca.certificate_pem, ca_key, 365,
            key_usage=cert.key_usage, extended_key_usage=cert.extended_key_usage,
        )
        parsed = x509.load_pem_x509_certificate(cert_pem.encode())
        cert.certificate_pem = cert_pem
        cert.status = CertificateStatus.active
        cert.serial_number = format(parsed.serial_number, "x")
        cert.not_before = parsed.not_valid_before_utc
        cert.not_after = parsed.not_valid_after_utc
        cert.approved_by = user_id
        db.commit()
        db.refresh(cert)
        audit.log(db, user_id, AuditAction.approved_request, AuditResourceType.certificate, cert.id)
        return cert

    def deny(self, db: Session, user_id: str, cert_id: str) -> Certificate:
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if cert.status != CertificateStatus.pending:
            raise ValueError("Certificate is not pending")
        cert.status = CertificateStatus.denied
        db.commit()
        db.refresh(cert)
        audit.log(db, user_id, AuditAction.denied_request, AuditResourceType.certificate, cert.id)
        return cert

    def revoke(self, db: Session, user_id: str, cert_id: str, reason: str) -> Certificate:
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if cert.status != CertificateStatus.active:
            raise ValueError("Certificate is not active")
        cert.status = CertificateStatus.revoked
        cert.revocation_date = datetime.now(timezone.utc)
        cert.revocation_reason = RevocationReason(reason)
        db.commit()
        db.refresh(cert)
        audit.log(db, user_id, AuditAction.revoked_cert, AuditResourceType.certificate, cert.id)
        return cert

    def renew(self, db: Session, user_id: str, cert_id: str, validity_days: int = 365) -> Certificate:
        old_cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not old_cert:
            raise ValueError("Certificate not found")
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == old_cert.ca_id).first()

        data = {
            "ca_id": old_cert.ca_id,
            "subject": dict(pair.split("=") for pair in old_cert.subject_dn.split(", ")),
            "san": old_cert.san or [],
            "type": old_cert.type.value,
            "key_algorithm": old_cert.key_algorithm.value,
            "key_size": old_cert.key_size,
            "validity_days": validity_days,
            "key_usage": old_cert.key_usage,
            "extended_key_usage": old_cert.extended_key_usage,
        }
        new_cert = self.request_certificate(db, user_id, data)
        audit.log(db, user_id, AuditAction.renewed_cert, AuditResourceType.certificate, new_cert.id, {"renewed_from": cert_id})
        return new_cert

    def download(self, cert_id: str, fmt: str, db: Session, passphrase: str | None = None) -> bytes:
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert or not cert.certificate_pem:
            raise ValueError("Certificate not found or not yet issued")

        key_pem = None
        if cert.private_key_encrypted and fmt == "pkcs12":
            key_pem = decrypt_private_key(cert.private_key_encrypted, settings.PKI_MASTER_KEY)

        return crypto.convert_format(cert.certificate_pem, key_pem, fmt, passphrase=passphrase)
```

- [ ] **Step 5: Create certificates router**

`backend/app/routers/certificates.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import Certificate, CertificateStatus, User, UserRole
from app.schemas.certificate import (
    CertificateCreate,
    CertificateListResponse,
    CertificateResponse,
    CertificateRevoke,
    CSRSubmit,
)
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])
cert_service = CertificateService()


@router.get("/", response_model=CertificateListResponse)
def list_certificates(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    ca_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    query = db.query(Certificate)
    if ca_id:
        query = query.filter(Certificate.ca_id == ca_id)
    if status:
        query = query.filter(Certificate.status == CertificateStatus(status))
    total = query.count()
    items = query.order_by(Certificate.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return CertificateListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
def create_certificate(
    body: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.requester)),
):
    data = body.model_dump()
    data["subject"] = body.subject.model_dump(exclude_none=True)
    data["san"] = [s.model_dump() for s in body.san] if body.san else []
    try:
        cert = cert_service.request_certificate(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return cert


@router.post("/csr", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
def submit_csr(
    body: CSRSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.requester)),
):
    try:
        cert = cert_service.submit_csr(db, current_user.id, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return cert


@router.get("/{cert_id}", response_model=CertificateResponse)
def get_certificate(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor, UserRole.requester)),
):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if current_user.role == UserRole.requester and cert.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return cert


@router.post("/{cert_id}/approve", response_model=CertificateResponse)
def approve_certificate(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    try:
        return cert_service.approve(db, current_user.id, cert_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{cert_id}/deny", response_model=CertificateResponse)
def deny_certificate(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    try:
        return cert_service.deny(db, current_user.id, cert_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{cert_id}/revoke", response_model=CertificateResponse)
def revoke_certificate(
    cert_id: str,
    body: CertificateRevoke,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    try:
        return cert_service.revoke(db, current_user.id, cert_id, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{cert_id}/renew", response_model=CertificateResponse)
def renew_certificate(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    try:
        return cert_service.renew(db, current_user.id, cert_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{cert_id}/download")
def download_certificate(
    cert_id: str,
    format: str = Query("pem", regex="^(pem|der|pkcs12)$"),
    passphrase: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.requester)),
):
    try:
        data = cert_service.download(cert_id, format, db, passphrase=passphrase)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    media_types = {"pem": "application/x-pem-file", "der": "application/x-x509-ca-cert", "pkcs12": "application/x-pkcs12"}
    extensions = {"pem": "pem", "der": "der", "pkcs12": "p12"}

    return Response(
        content=data,
        media_type=media_types[format],
        headers={"Content-Disposition": f"attachment; filename=certificate.{extensions[format]}"},
    )
```

- [ ] **Step 6: Register certificates router in main.py**

```python
from app.routers import auth, users, audit, cas, certificates

app.include_router(certificates.router)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_certificates.py -v`

Expected: All 7 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/certificate_service.py backend/app/schemas/certificate.py backend/app/routers/certificates.py backend/tests/test_certificates.py backend/app/main.py
git commit -m "feat: certificate lifecycle — issue, CSR submit, approve, deny, revoke, renew, download"
```

---

## Task 11: CRL Service & Router

**Files:**
- Create: `backend/app/services/crl_service.py`
- Create: `backend/app/schemas/crl.py`
- Create: `backend/app/routers/crl.py`
- Create: `backend/tests/test_crl.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest


@pytest.fixture
def ca_with_revoked(client, admin_headers):
    ca = client.post(
        "/api/v1/cas",
        json={
            "name": "CRL CA",
            "subject": {"CN": "CRL CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
            "auto_approve": True,
        },
        headers=admin_headers,
    ).json()

    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": ca["id"],
            "subject": {"CN": "revoked.example.com"},
            "san": [{"type": "DNS", "value": "revoked.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()

    client.post(f"/api/v1/certificates/{cert['id']}/revoke", json={"reason": "key_compromise"}, headers=admin_headers)
    return ca


def test_generate_crl(client, admin_headers, ca_with_revoked):
    response = client.post(f"/api/v1/cas/{ca_with_revoked['id']}/crl/generate", headers=admin_headers)
    assert response.status_code == 200
    assert "-----BEGIN X509 CRL-----" in response.json()["crl_pem"]


def test_download_crl(client, admin_headers, ca_with_revoked):
    client.post(f"/api/v1/cas/{ca_with_revoked['id']}/crl/generate", headers=admin_headers)
    response = client.get(f"/api/v1/cas/{ca_with_revoked['id']}/crl", headers=admin_headers)
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_crl.py -v`

Expected: FAIL

- [ ] **Step 3: Implement crl_service.py**

```python
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AuditAction,
    AuditResourceType,
    Certificate,
    CertificateAuthority,
    CertificateRevocationList,
    CertificateStatus,
)
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService
from app.services.encryption import decrypt_private_key

crypto = CryptoService()
audit = AuditService()


class CRLService:
    def generate_crl(self, db: Session, ca_id: str, user_id: str | None = None) -> CertificateRevocationList:
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
        if not ca:
            raise ValueError("CA not found")

        ca_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)

        revoked = db.query(Certificate).filter(
            Certificate.ca_id == ca_id,
            Certificate.status == CertificateStatus.revoked,
        ).all()

        revoked_entries = [
            {"serial_number": c.serial_number, "revocation_date": c.revocation_date}
            for c in revoked
        ]

        last_crl = (
            db.query(CertificateRevocationList)
            .filter(CertificateRevocationList.ca_id == ca_id)
            .order_by(CertificateRevocationList.crl_number.desc())
            .first()
        )
        crl_number = (last_crl.crl_number + 1) if last_crl else 1

        crl_pem = crypto.generate_crl(
            ca.certificate_pem, ca_key, revoked_entries,
            next_update_days=max(1, ca.crl_regen_interval_hours // 24),
            crl_number=crl_number,
        )

        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        crl_record = CertificateRevocationList(
            ca_id=ca_id,
            crl_pem=crl_pem,
            this_update=now,
            next_update=now + timedelta(hours=ca.crl_regen_interval_hours),
            crl_number=crl_number,
        )
        db.add(crl_record)
        db.commit()
        db.refresh(crl_record)

        if user_id:
            audit.log(db, user_id, AuditAction.generated_crl, AuditResourceType.crl, crl_record.id)

        return crl_record

    def get_latest_crl(self, db: Session, ca_id: str) -> CertificateRevocationList | None:
        return (
            db.query(CertificateRevocationList)
            .filter(CertificateRevocationList.ca_id == ca_id)
            .order_by(CertificateRevocationList.crl_number.desc())
            .first()
        )
```

- [ ] **Step 4: Create CRL schemas and router**

`backend/app/schemas/crl.py`:

```python
from pydantic import BaseModel


class CRLResponse(BaseModel):
    id: str
    ca_id: str
    crl_pem: str
    this_update: str
    next_update: str
    crl_number: int
    created_at: str

    model_config = {"from_attributes": True}
```

`backend/app/routers/crl.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.crl import CRLResponse
from app.services.crl_service import CRLService

router = APIRouter(prefix="/api/v1/cas", tags=["crl"])
crl_service = CRLService()


@router.post("/{ca_id}/crl/generate", response_model=CRLResponse)
def generate_crl(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    try:
        return crl_service.generate_crl(db, ca_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ca_id}/crl")
def download_crl(
    ca_id: str,
    db: Session = Depends(get_db),
):
    crl = crl_service.get_latest_crl(db, ca_id)
    if not crl:
        raise HTTPException(status_code=404, detail="No CRL found for this CA")
    return Response(
        content=crl.crl_pem.encode(),
        media_type="application/pkix-crl",
        headers={"Content-Disposition": "attachment; filename=crl.pem"},
    )
```

- [ ] **Step 5: Register CRL router in main.py**

```python
from app.routers import auth, users, audit, cas, certificates, crl

app.include_router(crl.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_crl.py -v`

Expected: All 2 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/crl_service.py backend/app/schemas/crl.py backend/app/routers/crl.py backend/tests/test_crl.py backend/app/main.py
git commit -m "feat: CRL generation and download endpoints"
```

---

## Task 12: OCSP Responder

**Files:**
- Create: `backend/app/services/ocsp_service.py`
- Create: `backend/app/routers/ocsp.py`
- Create: `backend/tests/test_ocsp.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from cryptography.x509 import ocsp, load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes, serialization


@pytest.fixture
def ca_and_cert(client, admin_headers):
    ca = client.post(
        "/api/v1/cas",
        json={
            "name": "OCSP CA",
            "subject": {"CN": "OCSP CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
            "auto_approve": True,
        },
        headers=admin_headers,
    ).json()
    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": ca["id"],
            "subject": {"CN": "ocsp.example.com"},
            "san": [{"type": "DNS", "value": "ocsp.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    return ca, cert


def test_ocsp_good_status(client, ca_and_cert):
    ca, cert = ca_and_cert
    ca_cert = load_pem_x509_certificate(ca["certificate_pem"].encode())
    ee_cert = load_pem_x509_certificate(cert["certificate_pem"].encode())

    ocsp_req = ocsp.OCSPRequestBuilder().add_certificate(ee_cert, ca_cert, hashes.SHA256()).build()
    req_bytes = ocsp_req.public_bytes(serialization.Encoding.DER)

    response = client.post(
        f"/api/v1/ocsp/{ca['id']}",
        content=req_bytes,
        headers={"Content-Type": "application/ocsp-request"},
    )
    assert response.status_code == 200
    ocsp_resp = ocsp.load_der_ocsp_response(response.content)
    assert ocsp_resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert ocsp_resp.certificate_status == ocsp.OCSPCertStatus.GOOD
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ocsp.py -v`

Expected: FAIL

- [ ] **Step 3: Implement ocsp_service.py**

```python
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Certificate, CertificateAuthority, CertificateStatus, OCSPSigningMode
from app.services.crypto_service import CryptoService
from app.services.encryption import decrypt_private_key

crypto = CryptoService()


class OCSPService:
    def handle_request(self, db: Session, ca_id: str, request_bytes: bytes) -> bytes:
        from cryptography.x509 import ocsp

        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
        if not ca:
            return ocsp.OCSPResponseBuilder.build_unsuccessful(
                ocsp.OCSPResponseStatus.UNAUTHORIZED
            ).public_bytes(__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.DER)

        ocsp_req = ocsp.load_der_ocsp_request(request_bytes)
        serial_hex = format(ocsp_req.serial_number, "x")

        cert_record = db.query(Certificate).filter(
            Certificate.ca_id == ca_id,
            Certificate.serial_number == serial_hex,
        ).first()

        if not cert_record or not cert_record.certificate_pem:
            cert_status = "unknown"
        elif cert_record.status == CertificateStatus.revoked:
            cert_status = "revoked"
        else:
            cert_status = "good"

        if ca.ocsp_signing_mode == OCSPSigningMode.dedicated_cert and ca.ocsp_signing_key_encrypted:
            signing_key = decrypt_private_key(ca.ocsp_signing_key_encrypted, settings.PKI_MASTER_KEY)
            signing_cert = ca.ocsp_signing_cert_pem
        else:
            signing_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)
            signing_cert = None

        if cert_status == "unknown":
            from cryptography.hazmat.primitives import serialization as ser
            return ocsp.OCSPResponseBuilder.build_unsuccessful(
                ocsp.OCSPResponseStatus.UNAUTHORIZED
            ).public_bytes(ser.Encoding.DER)

        return crypto.build_ocsp_response(
            ca.certificate_pem, signing_key, signing_cert, cert_record.certificate_pem,
            cert_status, revocation_time=cert_record.revocation_date if cert_status == "revoked" else None,
        )
```

- [ ] **Step 4: Create OCSP router**

`backend/app/routers/ocsp.py`:

```python
from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session
from fastapi import Depends

from app.dependencies import get_db
from app.services.ocsp_service import OCSPService

router = APIRouter(prefix="/api/v1/ocsp", tags=["ocsp"])
ocsp_service = OCSPService()


@router.post("/{ca_id}")
async def ocsp_responder_post(ca_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    response_bytes = ocsp_service.handle_request(db, ca_id, body)
    return Response(content=response_bytes, media_type="application/ocsp-response")


@router.get("/{ca_id}/{encoded_request}")
def ocsp_responder_get(ca_id: str, encoded_request: str, db: Session = Depends(get_db)):
    import base64
    request_bytes = base64.b64decode(encoded_request)
    response_bytes = ocsp_service.handle_request(db, ca_id, request_bytes)
    return Response(content=response_bytes, media_type="application/ocsp-response")
```

- [ ] **Step 5: Register OCSP router in main.py**

```python
from app.routers import auth, users, audit, cas, certificates, crl, ocsp

app.include_router(ocsp.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ocsp.py -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ocsp_service.py backend/app/routers/ocsp.py backend/tests/test_ocsp.py backend/app/main.py
git commit -m "feat: OCSP responder with configurable signing mode"
```

---

## Task 13: Dashboard Router

**Files:**
- Create: `backend/app/schemas/dashboard.py`
- Create: `backend/app/routers/dashboard.py`
- Create: `backend/tests/test_dashboard.py`

- [ ] **Step 1: Write failing tests**

```python
def test_dashboard_stats(client, admin_headers):
    response = client.get("/api/v1/dashboard/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "active_cas" in data
    assert "active_certs" in data
    assert "pending_requests" in data
    assert "expiring_soon" in data


def test_dashboard_expiring(client, admin_headers):
    response = client.get("/api/v1/dashboard/expiring", headers=admin_headers)
    assert response.status_code == 200
    assert "items" in response.json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_dashboard.py -v`

Expected: FAIL

- [ ] **Step 3: Create dashboard schemas**

`backend/app/schemas/dashboard.py`:

```python
from pydantic import BaseModel

from app.schemas.certificate import CertificateResponse


class DashboardStats(BaseModel):
    active_cas: int
    active_certs: int
    pending_requests: int
    expiring_soon: int


class ExpiringCertsResponse(BaseModel):
    items: list[CertificateResponse]
```

- [ ] **Step 4: Create dashboard router**

`backend/app/routers/dashboard.py`:

```python
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db, get_current_user
from app.models import (
    CAStatus,
    Certificate,
    CertificateAuthority,
    CertificateStatus,
    User,
)
from app.schemas.dashboard import DashboardStats, ExpiringCertsResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    active_cas = db.query(CertificateAuthority).filter(CertificateAuthority.status == CAStatus.active).count()
    active_certs = db.query(Certificate).filter(Certificate.status == CertificateStatus.active).count()
    pending = db.query(Certificate).filter(Certificate.status == CertificateStatus.pending).count()
    threshold = datetime.now(timezone.utc) + timedelta(days=settings.EXPIRY_WARNING_DAYS)
    expiring = (
        db.query(Certificate)
        .filter(
            Certificate.status == CertificateStatus.active,
            Certificate.not_after <= threshold,
        )
        .count()
    )
    return DashboardStats(active_cas=active_cas, active_certs=active_certs, pending_requests=pending, expiring_soon=expiring)


@router.get("/expiring", response_model=ExpiringCertsResponse)
def get_expiring(
    days: int = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    window = days if days else settings.EXPIRY_WARNING_DAYS
    threshold = datetime.now(timezone.utc) + timedelta(days=window)
    certs = (
        db.query(Certificate)
        .filter(
            Certificate.status == CertificateStatus.active,
            Certificate.not_after <= threshold,
        )
        .order_by(Certificate.not_after.asc())
        .all()
    )
    return ExpiringCertsResponse(items=certs)
```

- [ ] **Step 5: Register dashboard router in main.py**

```python
from app.routers import auth, users, audit, cas, certificates, crl, ocsp, dashboard

app.include_router(dashboard.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_dashboard.py -v`

Expected: All 2 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/dashboard.py backend/app/routers/dashboard.py backend/tests/test_dashboard.py backend/app/main.py
git commit -m "feat: dashboard stats and expiring certificates endpoints"
```

---

## Task 14: Background Scheduler

**Files:**
- Create: `backend/app/scheduler/__init__.py`
- Create: `backend/app/scheduler/jobs.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create scheduler/__init__.py**

```python
```

Empty file.

- [ ] **Step 2: Create scheduler/jobs.py**

```python
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CAStatus, Certificate, CertificateAuthority, CertificateRevocationList, CertificateStatus
from app.services.crl_service import CRLService

crl_service = CRLService()


def regenerate_crls():
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        cas = db.query(CertificateAuthority).filter(CertificateAuthority.status == CAStatus.active).all()
        for ca in cas:
            latest = (
                db.query(CertificateRevocationList)
                .filter(CertificateRevocationList.ca_id == ca.id)
                .order_by(CertificateRevocationList.crl_number.desc())
                .first()
            )
            if latest and latest.next_update > now:
                continue
            crl_service.generate_crl(db, ca.id)
    finally:
        db.close()


def check_expirations():
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        expired = (
            db.query(Certificate)
            .filter(
                Certificate.status == CertificateStatus.active,
                Certificate.not_after <= now,
            )
            .all()
        )
        for cert in expired:
            cert.status = CertificateStatus.expired
        if expired:
            db.commit()
    finally:
        db.close()
```

- [ ] **Step 3: Update main.py to start scheduler on startup**

Add to `backend/app/main.py`:

```python
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from app.scheduler.jobs import regenerate_crls, check_expirations

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app_instance):
    scheduler.add_job(regenerate_crls, "interval", hours=1, id="crl_regen")
    scheduler.add_job(check_expirations, "interval", hours=24, id="expiry_check")
    scheduler.start()
    yield
    scheduler.shutdown()

# Update the FastAPI app to use lifespan:
app = FastAPI(title="PKI Manager", version="0.1.0", lifespan=lifespan)
```

- [ ] **Step 4: Verify server starts with scheduler**

Run: `cd backend && uvicorn app.main:app --reload`

Expected: Server starts, no errors. Scheduler logs show jobs registered.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/ backend/app/main.py
git commit -m "feat: background scheduler for CRL regeneration and expiration checks"
```

---

## Task 15: Seed Script & Final Integration Test

**Files:**
- Create: `backend/seed.py`

- [ ] **Step 1: Create seed script for initial admin user**

```python
from app.database import SessionLocal, engine, Base
from app.models import User, UserRole
from app.services.auth_service import AuthService

Base.metadata.create_all(bind=engine)

auth = AuthService()
db = SessionLocal()

existing = db.query(User).filter(User.username == "admin").first()
if not existing:
    admin = User(
        username="admin",
        email="admin@pki.local",
        password_hash=auth.hash_password("admin"),
        role=UserRole.admin,
    )
    db.add(admin)
    db.commit()
    print("Admin user created (username: admin, password: admin)")
else:
    print("Admin user already exists")

db.close()
```

- [ ] **Step 2: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All tests pass

- [ ] **Step 3: Run seed script and test manually**

Run: `cd backend && python seed.py && uvicorn app.main:app --reload`

Then test:
- `POST /api/v1/auth/login` with `{"username": "admin", "password": "admin"}`
- Use the returned token to create a root CA
- Issue a certificate from that CA
- Download the certificate
- Check the dashboard stats

- [ ] **Step 4: Commit**

```bash
git add backend/seed.py
git commit -m "feat: seed script for initial admin user"
```

---

## Summary

This plan covers the complete backend with 15 tasks:

1. Project setup & config
2. SQLAlchemy models
3. Alembic migrations
4. Encryption service (AES-256-GCM)
5. Crypto service (all certificate operations)
6. Auth service & JWT dependencies
7. User management CRUD
8. Audit service & logging
9. CA management (root + intermediate + tree)
10. Certificate lifecycle (issue, CSR, approve, revoke, renew, download)
11. CRL generation & download
12. OCSP responder
13. Dashboard (stats + expiring)
14. Background scheduler
15. Seed script & integration test

**Frontend plan** will be written as a separate document after the backend is complete.
