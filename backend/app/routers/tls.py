import os
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db, require_role
from app.models import CertificateAuthority, User, UserRole
from app.services.certificate_service import CertificateService
from app.services.encryption import decrypt_private_key

router = APIRouter(prefix="/api/v1/tls", tags=["tls"])
cert_service = CertificateService()

CERT_PATH = os.path.join(settings.SSL_CERT_DIR, "cert.pem")
KEY_PATH = os.path.join(settings.SSL_CERT_DIR, "key.pem")


class TLSUpload(BaseModel):
    certificate_pem: str
    private_key_pem: str


class TLSIssue(BaseModel):
    ca_id: str
    common_name: str
    san: list[dict] | None = None
    validity_days: int = 365


class TLSInfoResponse(BaseModel):
    subject_dn: str | None = None
    issuer_dn: str | None = None
    not_before: str | None = None
    not_after: str | None = None
    serial_number: str | None = None
    self_signed: bool = False
    exists: bool = False


def _parse_cert_info(pem: str) -> dict:
    cert = x509.load_pem_x509_certificate(pem.encode())
    return {
        "subject_dn": cert.subject.rfc4514_string(),
        "issuer_dn": cert.issuer.rfc4514_string(),
        "not_before": cert.not_valid_before_utc.isoformat(),
        "not_after": cert.not_valid_after_utc.isoformat(),
        "serial_number": format(cert.serial_number, "x"),
        "self_signed": cert.subject == cert.issuer,
        "exists": True,
    }


@router.get("", response_model=TLSInfoResponse)
def get_tls_info(
    current_user: User = Depends(require_role(UserRole.admin)),
):
    if not os.path.exists(CERT_PATH):
        return TLSInfoResponse()
    try:
        with open(CERT_PATH, "r") as f:
            pem = f.read()
        return TLSInfoResponse(**_parse_cert_info(pem))
    except Exception:
        return TLSInfoResponse(exists=True)


@router.post("/upload")
def upload_tls_cert(
    body: TLSUpload,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    try:
        x509.load_pem_x509_certificate(body.certificate_pem.encode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid certificate PEM")
    try:
        serialization.load_pem_private_key(body.private_key_pem.encode(), password=None)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid private key PEM")

    os.makedirs(settings.SSL_CERT_DIR, exist_ok=True)
    with open(CERT_PATH, "w") as f:
        f.write(body.certificate_pem)
    with open(KEY_PATH, "w") as f:
        f.write(body.private_key_pem)

    return {"message": "TLS certificate updated. Restart the proxy container to apply.", **_parse_cert_info(body.certificate_pem)}


@router.post("/issue")
def issue_tls_cert(
    body: TLSIssue,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == body.ca_id).first()
    if not ca:
        raise HTTPException(status_code=400, detail="CA not found")

    san = body.san or [{"type": "DNS", "value": body.common_name}]
    data = {
        "ca_id": body.ca_id,
        "subject": {"CN": body.common_name},
        "san": san,
        "type": "server",
        "key_algorithm": "RSA",
        "key_size": 2048,
        "validity_days": body.validity_days,
    }
    cert = cert_service.request_certificate(db, current_user.id, data)

    if not cert.certificate_pem:
        raise HTTPException(status_code=400, detail="Certificate was not auto-approved. Enable auto-approve on the CA or approve it manually first.")

    key_pem = decrypt_private_key(cert.private_key_encrypted, settings.PKI_MASTER_KEY)

    os.makedirs(settings.SSL_CERT_DIR, exist_ok=True)
    with open(CERT_PATH, "w") as f:
        f.write(cert.certificate_pem)
    with open(KEY_PATH, "w") as f:
        f.write(key_pem if isinstance(key_pem, str) else key_pem.decode())

    return {"message": "TLS certificate issued and saved. Restart the proxy container to apply.", **_parse_cert_info(cert.certificate_pem)}
