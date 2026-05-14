# Import Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add import functionality for CAs and certificates from PEM, DER, and PKCS12 files, with auto-detection of parent CA relationships.

**Architecture:** New crypto service methods for parsing/converting formats, new service methods for import logic, new FastAPI endpoints accepting multipart uploads, new frontend modals on existing list pages.

**Tech Stack:** Python cryptography library, FastAPI UploadFile, React modals with file inputs

---

## File Structure

**Backend (new/modified):**
- Modify: `backend/app/services/crypto_service.py` — add parse_certificate, load_pkcs12, DER conversion, key verification
- Modify: `backend/app/models/audit_log.py` — add imported_ca, imported_cert actions
- Create: `backend/app/services/import_service.py` — import business logic
- Modify: `backend/app/routers/cas.py` — add POST /import endpoint
- Modify: `backend/app/routers/certificates.py` — add POST /import endpoint
- Create: `backend/tests/test_import.py`

**Frontend (new/modified):**
- Create: `frontend/src/api/import.js` — importCA(), importCertificate()
- Create: `frontend/src/components/forms/ImportCAModal.jsx`
- Create: `frontend/src/components/forms/ImportCertModal.jsx`
- Modify: `frontend/src/pages/cas/CAList.jsx` — add Import button + modal
- Modify: `frontend/src/pages/certificates/CertificateList.jsx` — add Import button + modal

---

## Task 1: Crypto Service — Import Helpers

**Files:**
- Modify: `backend/app/services/crypto_service.py`
- Create: `backend/tests/test_import.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_import.py`:

```python
import pytest
from app.services.crypto_service import CryptoService


@pytest.fixture
def crypto():
    return CryptoService()


@pytest.fixture
def root_ca(crypto):
    key = crypto.generate_key("RSA", 2048)
    cert = crypto.create_root_ca(key, {"CN": "Test Root CA", "O": "Test", "C": "US"}, 3650)
    return cert, key


class TestParseCertificate:
    def test_parse_pem_certificate(self, crypto, root_ca):
        cert_pem, _ = root_ca
        result = crypto.parse_certificate(cert_pem)
        assert result["subject"]["CN"] == "Test Root CA"
        assert result["issuer"]["CN"] == "Test Root CA"
        assert result["is_ca"] is True
        assert "serial_number" in result
        assert "not_before" in result
        assert "not_after" in result
        assert "key_algorithm" in result

    def test_parse_end_entity_cert(self, crypto, root_ca):
        ca_cert, ca_key = root_ca
        ee_key = crypto.generate_key("RSA", 2048)
        csr = crypto.generate_csr(ee_key, {"CN": "test.example.com"}, [{"type": "DNS", "value": "test.example.com"}])
        ee_cert = crypto.sign_csr(csr, ca_cert, ca_key, 365)
        result = crypto.parse_certificate(ee_cert)
        assert result["subject"]["CN"] == "test.example.com"
        assert result["is_ca"] is False
        assert len(result["sans"]) == 1


class TestDERConversion:
    def test_der_to_pem_cert(self, crypto, root_ca):
        cert_pem, _ = root_ca
        der_bytes = crypto.convert_format(cert_pem, None, "der")
        converted_pem = crypto.der_to_pem_cert(der_bytes)
        assert "-----BEGIN CERTIFICATE-----" in converted_pem
        parsed = crypto.parse_certificate(converted_pem)
        assert parsed["subject"]["CN"] == "Test Root CA"

    def test_der_to_pem_key(self, crypto):
        key_pem = crypto.generate_key("RSA", 2048)
        from cryptography.hazmat.primitives import serialization
        key_obj = serialization.load_pem_private_key(key_pem.encode(), password=None)
        der_bytes = key_obj.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        converted_pem = crypto.der_to_pem_key(der_bytes)
        assert "-----BEGIN PRIVATE KEY-----" in converted_pem


class TestKeyVerification:
    def test_matching_key(self, crypto, root_ca):
        cert_pem, key_pem = root_ca
        assert crypto.verify_key_matches_cert(key_pem, cert_pem) is True

    def test_mismatched_key(self, crypto, root_ca):
        cert_pem, _ = root_ca
        other_key = crypto.generate_key("RSA", 2048)
        assert crypto.verify_key_matches_cert(other_key, cert_pem) is False


class TestLoadPKCS12:
    def test_load_pkcs12(self, crypto, root_ca):
        cert_pem, key_pem = root_ca
        p12_bytes = crypto.convert_format(cert_pem, key_pem, "pkcs12", passphrase="test123")
        loaded_cert, loaded_key, chain = crypto.load_pkcs12(p12_bytes, "test123")
        assert "-----BEGIN CERTIFICATE-----" in loaded_cert
        assert "-----BEGIN" in loaded_key
        assert crypto.verify_key_matches_cert(loaded_key, loaded_cert) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_import.py -v`

Expected: FAIL — AttributeError on missing methods

- [ ] **Step 3: Add methods to CryptoService**

Add these methods to `backend/app/services/crypto_service.py`:

```python
def parse_certificate(self, cert_pem: str) -> dict:
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    subject = {}
    for attr in cert.subject:
        for key, oid in _NAME_OID_MAP.items():
            if attr.oid == oid:
                subject[key] = attr.value
    issuer = {}
    for attr in cert.issuer:
        for key, oid in _NAME_OID_MAP.items():
            if attr.oid == oid:
                issuer[key] = attr.value

    is_ca = False
    try:
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        is_ca = bc.value.ca
    except x509.ExtensionNotFound:
        pass

    sans = []
    try:
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
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

    key_algorithm = "RSA"
    key_size = 0
    pub = cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        key_algorithm = "RSA"
        key_size = pub.key_size
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        key_algorithm = "EC"
        key_size = pub.key_size

    return {
        "subject": subject,
        "issuer": issuer,
        "subject_dn": cert.subject.rfc4514_string(),
        "issuer_dn": cert.issuer.rfc4514_string(),
        "serial_number": format(cert.serial_number, "x"),
        "not_before": cert.not_valid_before_utc,
        "not_after": cert.not_valid_after_utc,
        "is_ca": is_ca,
        "key_algorithm": key_algorithm,
        "key_size": key_size,
        "sans": sans,
    }

def load_pkcs12(self, data: bytes, passphrase: str | None = None) -> tuple[str, str, list[str]]:
    from cryptography.hazmat.primitives.serialization import pkcs12
    pw = passphrase.encode() if passphrase else None
    private_key, certificate, chain = pkcs12.load_key_and_certificates(data, pw)
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    chain_pems = [c.public_bytes(serialization.Encoding.PEM).decode() for c in (chain or [])]
    return cert_pem, key_pem, chain_pems

def der_to_pem_cert(self, der_bytes: bytes) -> str:
    cert = x509.load_der_x509_certificate(der_bytes)
    return cert.public_bytes(serialization.Encoding.PEM).decode()

def der_to_pem_key(self, der_bytes: bytes) -> str:
    key = serialization.load_der_private_key(der_bytes, password=None)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

def verify_key_matches_cert(self, key_pem: str, cert_pem: str) -> bool:
    key = self._load_private_key(key_pem)
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    key_pub_bytes = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    cert_pub_bytes = cert.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return key_pub_bytes == cert_pub_bytes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_import.py -v`

Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/crypto_service.py backend/tests/test_import.py
git commit -m "feat: crypto service import helpers — parse cert, load PKCS12, DER conversion, key verification"
```

---

## Task 2: Import Service & Backend Endpoints

**Files:**
- Modify: `backend/app/models/audit_log.py` — add new audit actions
- Create: `backend/app/services/import_service.py`
- Modify: `backend/app/routers/cas.py` — add import endpoint
- Modify: `backend/app/routers/certificates.py` — add import endpoint
- Modify: `backend/tests/test_import.py` — add API tests

- [ ] **Step 1: Add audit actions**

Add to the `AuditAction` enum in `backend/app/models/audit_log.py`:

```python
imported_ca = "imported_ca"
imported_cert = "imported_cert"
```

- [ ] **Step 2: Create import_service.py**

Create `backend/app/services/import_service.py`:

```python
from cryptography import x509

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AuditAction,
    AuditResourceType,
    CAStatus,
    CAType,
    Certificate,
    CertificateAuthority,
    CertificateStatus,
    CertificateType,
    KeyAlgorithm,
)
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService
from app.services.encryption import encrypt_private_key

crypto = CryptoService()
audit = AuditService()


class ImportService:
    def _detect_format_and_get_pem(self, cert_data: bytes, key_data: bytes | None, pkcs12_data: bytes | None, passphrase: str | None) -> tuple[str, str | None]:
        if pkcs12_data:
            cert_pem, key_pem, _ = crypto.load_pkcs12(pkcs12_data, passphrase)
            return cert_pem, key_pem

        if cert_data.startswith(b"-----BEGIN"):
            cert_pem = cert_data.decode()
        else:
            cert_pem = crypto.der_to_pem_cert(cert_data)

        key_pem = None
        if key_data:
            if key_data.startswith(b"-----BEGIN"):
                key_pem = key_data.decode()
            else:
                key_pem = crypto.der_to_pem_key(key_data)

        return cert_pem, key_pem

    def _find_parent_ca(self, db: Session, cert_pem: str) -> CertificateAuthority | None:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        issuer_dn = cert.issuer.rfc4514_string()
        subject_dn = cert.subject.rfc4514_string()
        if issuer_dn == subject_dn:
            return None
        cas = db.query(CertificateAuthority).all()
        for ca in cas:
            ca_cert = x509.load_pem_x509_certificate(ca.certificate_pem.encode())
            if ca_cert.subject == cert.issuer:
                return ca
        return None

    def import_ca(
        self, db: Session, user_id: str, name: str,
        cert_data: bytes | None, key_data: bytes | None,
        pkcs12_data: bytes | None, passphrase: str | None,
    ) -> tuple[CertificateAuthority, bool]:
        cert_pem, key_pem = self._detect_format_and_get_pem(cert_data, key_data, pkcs12_data, passphrase)

        if not key_pem:
            raise ValueError("Private key is required for CA import")

        parsed = crypto.parse_certificate(cert_pem)

        if not parsed["is_ca"]:
            raise ValueError("Certificate does not have CA:TRUE basic constraint")

        if not crypto.verify_key_matches_cert(key_pem, cert_pem):
            raise ValueError("Private key does not match the certificate")

        parent = self._find_parent_ca(db, cert_pem)
        parent_detected = parent is not None

        ca = CertificateAuthority(
            name=name,
            type=CAType.intermediate if parent else CAType.root,
            status=CAStatus.active,
            parent_ca_id=parent.id if parent else None,
            private_key_encrypted=encrypt_private_key(key_pem, settings.PKI_MASTER_KEY),
            certificate_pem=cert_pem,
            key_algorithm=KeyAlgorithm(parsed["key_algorithm"]),
            key_size=parsed["key_size"],
            subject_dn=parsed["subject_dn"],
            serial_number=parsed["serial_number"],
            not_before=parsed["not_before"],
            not_after=parsed["not_after"],
            created_by=user_id,
        )
        db.add(ca)
        db.commit()
        db.refresh(ca)
        audit.log(db, user_id, AuditAction.imported_ca, AuditResourceType.ca, ca.id, {"name": name, "parent_detected": parent_detected})
        return ca, parent_detected

    def import_certificate(
        self, db: Session, user_id: str,
        cert_data: bytes | None, key_data: bytes | None,
        pkcs12_data: bytes | None, passphrase: str | None,
        ca_id: str | None,
    ) -> tuple[Certificate, bool]:
        cert_pem, key_pem = self._detect_format_and_get_pem(cert_data, key_data, pkcs12_data, passphrase)

        if key_pem and not crypto.verify_key_matches_cert(key_pem, cert_pem):
            raise ValueError("Private key does not match the certificate")

        parsed = crypto.parse_certificate(cert_pem)

        parent = self._find_parent_ca(db, cert_pem)
        parent_detected = parent is not None
        resolved_ca_id = parent.id if parent else ca_id

        if not resolved_ca_id:
            raise ValueError("Could not auto-detect issuing CA. Please select one manually.")

        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == resolved_ca_id).first()
        if not ca:
            raise ValueError("Specified CA not found")

        cert = Certificate(
            ca_id=resolved_ca_id,
            status=CertificateStatus.active,
            type=CertificateType.server,
            private_key_encrypted=encrypt_private_key(key_pem, settings.PKI_MASTER_KEY) if key_pem else None,
            certificate_pem=cert_pem,
            key_algorithm=KeyAlgorithm(parsed["key_algorithm"]),
            key_size=parsed["key_size"],
            subject_dn=parsed["subject_dn"],
            serial_number=parsed["serial_number"],
            san=parsed["sans"],
            not_before=parsed["not_before"],
            not_after=parsed["not_after"],
            requested_by=user_id,
            approved_by=user_id,
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
        audit.log(db, user_id, AuditAction.imported_cert, AuditResourceType.certificate, cert.id, {"parent_detected": parent_detected})
        return cert, parent_detected
```

- [ ] **Step 3: Add import endpoint to CAs router**

Add to `backend/app/routers/cas.py`:

```python
from fastapi import File, Form, UploadFile
from app.services.import_service import ImportService

import_service = ImportService()


@router.post("/import", response_model=CAResponse, status_code=status.HTTP_201_CREATED)
async def import_ca(
    name: str = Form(...),
    cert_file: UploadFile | None = File(None),
    key_file: UploadFile | None = File(None),
    pkcs12_file: UploadFile | None = File(None),
    passphrase: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    cert_data = await cert_file.read() if cert_file else None
    key_data = await key_file.read() if key_file else None
    pkcs12_data = await pkcs12_file.read() if pkcs12_file else None
    if not cert_data and not pkcs12_data:
        raise HTTPException(status_code=400, detail="Provide either cert_file or pkcs12_file")
    try:
        ca, parent_detected = import_service.import_ca(db, current_user.id, name, cert_data, key_data, pkcs12_data, passphrase)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ca
```

- [ ] **Step 4: Add import endpoint to certificates router**

Add to `backend/app/routers/certificates.py`:

```python
from fastapi import File, Form, UploadFile
from app.services.import_service import ImportService

import_service = ImportService()


@router.post("/import", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def import_certificate(
    cert_file: UploadFile | None = File(None),
    key_file: UploadFile | None = File(None),
    pkcs12_file: UploadFile | None = File(None),
    passphrase: str | None = Form(None),
    ca_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.requester)),
):
    cert_data = await cert_file.read() if cert_file else None
    key_data = await key_file.read() if key_file else None
    pkcs12_data = await pkcs12_file.read() if pkcs12_file else None
    if not cert_data and not pkcs12_data:
        raise HTTPException(status_code=400, detail="Provide either cert_file or pkcs12_file")
    try:
        cert, parent_detected = import_service.import_certificate(db, current_user.id, cert_data, key_data, pkcs12_data, passphrase, ca_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return cert
```

- [ ] **Step 5: Add API integration tests**

Append to `backend/tests/test_import.py`:

```python
import io


def test_import_root_ca_pem(client, admin_headers):
    from app.services.crypto_service import CryptoService
    crypto = CryptoService()
    key = crypto.generate_key("RSA", 2048)
    cert = crypto.create_root_ca(key, {"CN": "Imported Root CA", "O": "Test", "C": "US"}, 3650)

    response = client.post(
        "/api/v1/cas/import",
        data={"name": "Imported Root"},
        files={
            "cert_file": ("cert.pem", io.BytesIO(cert.encode()), "application/x-pem-file"),
            "key_file": ("key.pem", io.BytesIO(key.encode()), "application/x-pem-file"),
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Imported Root"
    assert data["type"] == "root"


def test_import_intermediate_ca_auto_detects_parent(client, admin_headers):
    from app.services.crypto_service import CryptoService
    crypto = CryptoService()

    root_key = crypto.generate_key("RSA", 2048)
    root_cert = crypto.create_root_ca(root_key, {"CN": "Parent Root CA", "O": "Test", "C": "US"}, 3650)

    client.post(
        "/api/v1/cas/import",
        data={"name": "Parent Root"},
        files={
            "cert_file": ("cert.pem", io.BytesIO(root_cert.encode()), "application/x-pem-file"),
            "key_file": ("key.pem", io.BytesIO(root_key.encode()), "application/x-pem-file"),
        },
        headers=admin_headers,
    )

    int_key = crypto.generate_key("RSA", 2048)
    int_cert = crypto.create_intermediate_ca(int_key, {"CN": "Child CA", "O": "Test", "C": "US"}, root_cert, root_key, 1825)

    response = client.post(
        "/api/v1/cas/import",
        data={"name": "Child CA"},
        files={
            "cert_file": ("cert.pem", io.BytesIO(int_cert.encode()), "application/x-pem-file"),
            "key_file": ("key.pem", io.BytesIO(int_key.encode()), "application/x-pem-file"),
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "intermediate"
    assert data["parent_ca_id"] is not None


def test_import_certificate_pem(client, admin_headers):
    from app.services.crypto_service import CryptoService
    crypto = CryptoService()

    ca_key = crypto.generate_key("RSA", 2048)
    ca_cert = crypto.create_root_ca(ca_key, {"CN": "Import Test CA", "O": "Test", "C": "US"}, 3650)
    ca_resp = client.post(
        "/api/v1/cas/import",
        data={"name": "Import Test CA"},
        files={
            "cert_file": ("cert.pem", io.BytesIO(ca_cert.encode()), "application/x-pem-file"),
            "key_file": ("key.pem", io.BytesIO(ca_key.encode()), "application/x-pem-file"),
        },
        headers=admin_headers,
    ).json()

    ee_key = crypto.generate_key("RSA", 2048)
    csr = crypto.generate_csr(ee_key, {"CN": "imported.example.com"}, [{"type": "DNS", "value": "imported.example.com"}])
    ee_cert = crypto.sign_csr(csr, ca_cert, ca_key, 365)

    response = client.post(
        "/api/v1/certificates/import",
        files={
            "cert_file": ("cert.pem", io.BytesIO(ee_cert.encode()), "application/x-pem-file"),
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "active"
    assert data["ca_id"] == ca_resp["id"]


def test_import_ca_rejects_non_ca_cert(client, admin_headers):
    from app.services.crypto_service import CryptoService
    crypto = CryptoService()

    ca_key = crypto.generate_key("RSA", 2048)
    ca_cert = crypto.create_root_ca(ca_key, {"CN": "CA", "O": "Test", "C": "US"}, 3650)
    ee_key = crypto.generate_key("RSA", 2048)
    csr = crypto.generate_csr(ee_key, {"CN": "not-a-ca.com"})
    ee_cert = crypto.sign_csr(csr, ca_cert, ca_key, 365)

    response = client.post(
        "/api/v1/cas/import",
        data={"name": "Not A CA"},
        files={
            "cert_file": ("cert.pem", io.BytesIO(ee_cert.encode()), "application/x-pem-file"),
            "key_file": ("key.pem", io.BytesIO(ee_key.encode()), "application/x-pem-file"),
        },
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "CA:TRUE" in response.json()["detail"]
```

- [ ] **Step 6: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All tests pass (39 existing + 11 new = 50)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/import_service.py backend/app/models/audit_log.py backend/app/routers/cas.py backend/app/routers/certificates.py backend/tests/test_import.py
git commit -m "feat: import endpoints for CAs and certificates with auto-detect parent and format support"
```

---

## Task 3: Frontend — Import Modals & Integration

**Files:**
- Create: `frontend/src/api/import.js`
- Create: `frontend/src/components/forms/ImportCAModal.jsx`
- Create: `frontend/src/components/forms/ImportCertModal.jsx`
- Modify: `frontend/src/pages/cas/CAList.jsx`
- Modify: `frontend/src/pages/certificates/CertificateList.jsx`

- [ ] **Step 1: Create API module**

Create `frontend/src/api/import.js`:

```js
import client from './client'

export const importCA = async (formData) => {
  const { data } = await client.post('/cas/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const importCertificate = async (formData) => {
  const { data } = await client.post('/certificates/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
```

- [ ] **Step 2: Create ImportCAModal**

Create `frontend/src/components/forms/ImportCAModal.jsx`:

```jsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { importCA } from '../../api/import'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'

const formatOptions = [
  { value: 'pem', label: 'PEM / DER' },
  { value: 'pkcs12', label: 'PKCS12 / PFX' },
]

export default function ImportCAModal({ isOpen, onClose }) {
  const queryClient = useQueryClient()
  const [format, setFormat] = useState('pem')
  const [name, setName] = useState('')
  const [certFile, setCertFile] = useState(null)
  const [keyFile, setKeyFile] = useState(null)
  const [pkcs12File, setPkcs12File] = useState(null)
  const [passphrase, setPassphrase] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: importCA,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cas'] })
      queryClient.invalidateQueries({ queryKey: ['cas-tree'] })
      onClose()
      resetForm()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Import failed'),
  })

  const resetForm = () => {
    setFormat('pem')
    setName('')
    setCertFile(null)
    setKeyFile(null)
    setPkcs12File(null)
    setPassphrase('')
    setError('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    const formData = new FormData()
    formData.append('name', name)
    if (format === 'pkcs12') {
      if (pkcs12File) formData.append('pkcs12_file', pkcs12File)
      if (passphrase) formData.append('passphrase', passphrase)
    } else {
      if (certFile) formData.append('cert_file', certFile)
      if (keyFile) formData.append('key_file', keyFile)
    }
    mutation.mutate(formData)
  }

  return (
    <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm() }} title="Import CA" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="CA Name *" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Imported Root CA" />
        <Select label="Format" options={formatOptions} value={format} onChange={(e) => setFormat(e.target.value)} />

        {format === 'pem' ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Certificate File *</label>
              <input type="file" accept=".pem,.crt,.cer,.der" onChange={(e) => setCertFile(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Private Key File *</label>
              <input type="file" accept=".pem,.key,.der" onChange={(e) => setKeyFile(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">PKCS12 / PFX File *</label>
              <input type="file" accept=".p12,.pfx" onChange={(e) => setPkcs12File(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
            <Input label="Passphrase" type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
          </>
        )}

        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={() => { onClose(); resetForm() }}>Cancel</Button>
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Importing...' : 'Import CA'}</Button>
        </div>
      </form>
    </Modal>
  )
}
```

- [ ] **Step 3: Create ImportCertModal**

Create `frontend/src/components/forms/ImportCertModal.jsx`:

```jsx
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { importCertificate } from '../../api/import'
import { getCAs } from '../../api/cas'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'

const formatOptions = [
  { value: 'pem', label: 'PEM / DER' },
  { value: 'pkcs12', label: 'PKCS12 / PFX' },
]

export default function ImportCertModal({ isOpen, onClose }) {
  const queryClient = useQueryClient()
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100), enabled: isOpen })

  const [format, setFormat] = useState('pem')
  const [certFile, setCertFile] = useState(null)
  const [keyFile, setKeyFile] = useState(null)
  const [pkcs12File, setPkcs12File] = useState(null)
  const [passphrase, setPassphrase] = useState('')
  const [caId, setCaId] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: importCertificate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      onClose()
      resetForm()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Import failed'),
  })

  const resetForm = () => {
    setFormat('pem')
    setCertFile(null)
    setKeyFile(null)
    setPkcs12File(null)
    setPassphrase('')
    setCaId('')
    setError('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    const formData = new FormData()
    if (format === 'pkcs12') {
      if (pkcs12File) formData.append('pkcs12_file', pkcs12File)
      if (passphrase) formData.append('passphrase', passphrase)
    } else {
      if (certFile) formData.append('cert_file', certFile)
      if (keyFile) formData.append('key_file', keyFile)
    }
    if (caId) formData.append('ca_id', caId)
    mutation.mutate(formData)
  }

  const caOptions = [{ value: '', label: 'Auto-detect (or select)' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]

  return (
    <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm() }} title="Import Certificate" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Select label="Format" options={formatOptions} value={format} onChange={(e) => setFormat(e.target.value)} />

        {format === 'pem' ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Certificate File *</label>
              <input type="file" accept=".pem,.crt,.cer,.der" onChange={(e) => setCertFile(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Private Key File (optional)</label>
              <input type="file" accept=".pem,.key,.der" onChange={(e) => setKeyFile(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">PKCS12 / PFX File *</label>
              <input type="file" accept=".p12,.pfx" onChange={(e) => setPkcs12File(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
            <Input label="Passphrase" type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
          </>
        )}

        <Select label="Issuing CA" options={caOptions} value={caId} onChange={(e) => setCaId(e.target.value)} />
        <p className="text-xs text-gray-500 dark:text-gray-400">Leave as auto-detect to match by issuer field. Select manually if auto-detect fails.</p>

        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={() => { onClose(); resetForm() }}>Cancel</Button>
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Importing...' : 'Import Certificate'}</Button>
        </div>
      </form>
    </Modal>
  )
}
```

- [ ] **Step 4: Add Import button to CAList page**

In `frontend/src/pages/cas/CAList.jsx`, add the import modal. Add at the top:

```jsx
import { useState } from 'react'
import ImportCAModal from '../../components/forms/ImportCAModal'
```

Add state: `const [showImport, setShowImport] = useState(false)`

Add button next to "Create Root CA": `<Button variant="secondary" onClick={() => setShowImport(true)}>Import CA</Button>`

Add modal before closing `</div>`: `<ImportCAModal isOpen={showImport} onClose={() => setShowImport(false)} />`

- [ ] **Step 5: Add Import button to CertificateList page**

In `frontend/src/pages/certificates/CertificateList.jsx`, same pattern:

```jsx
import ImportCertModal from '../../components/forms/ImportCertModal'
```

Add state, button ("Import" next to "Submit CSR"), and modal.

- [ ] **Step 6: Build frontend to verify**

Run: `cd frontend && npm run build`

Expected: Build succeeds with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/import.js frontend/src/components/forms/ImportCAModal.jsx frontend/src/components/forms/ImportCertModal.jsx frontend/src/pages/cas/CAList.jsx frontend/src/pages/certificates/CertificateList.jsx
git commit -m "feat: import modals for CAs and certificates on list pages"
```

---

## Summary

3 tasks:

1. **Crypto service helpers** — parse_certificate, load_pkcs12, DER conversion, key verification (7 tests)
2. **Import service + endpoints** — import logic with auto-detect parent, multipart upload endpoints (4 API tests)
3. **Frontend modals** — ImportCAModal and ImportCertModal inline on list pages
