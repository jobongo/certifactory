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
from app.services.settings_service import SettingsService

crypto = CryptoService()
audit = AuditService()
settings_svc = SettingsService()


class CertificateService:
    def _get_next_serial(self, db: Session, ca_id: str) -> str:
        count = db.query(Certificate).filter(Certificate.ca_id == ca_id).count()
        return format(count + 1, "x")

    def _extract_cn(self, subject_dn: str) -> str | None:
        for part in subject_dn.split(","):
            key, _, value = part.strip().partition("=")
            if key.strip().upper() == "CN":
                return value.strip()
        return None

    def _check_duplicate_cn(self, db: Session, ca_id: str, subject_dn: str):
        cn = self._extract_cn(subject_dn)
        if not cn:
            return
        existing = (
            db.query(Certificate)
            .filter(
                Certificate.ca_id == ca_id,
                Certificate.status.in_([CertificateStatus.active, CertificateStatus.pending]),
            )
            .all()
        )
        for cert in existing:
            if self._extract_cn(cert.subject_dn) == cn:
                raise ValueError(f"A certificate with CN={cn} already exists for this CA")

    def request_certificate(self, db: Session, user_id: str, data: dict, _skip_duplicate_check: bool = False) -> Certificate:
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == data["ca_id"]).first()
        if not ca:
            raise ValueError("CA not found")
        if ca.status != CAStatus.active:
            raise ValueError("CA is not active")

        subject_dn = ", ".join(f"{k}={v}" for k, v in data["subject"].items())
        if not _skip_duplicate_check:
            self._check_duplicate_cn(db, ca.id, subject_dn)

        key_pem = crypto.generate_key(data["key_algorithm"], data["key_size"])
        subject = data["subject"]
        sans = data.get("san", [])
        csr_pem = crypto.generate_csr(key_pem, subject, [s if isinstance(s, dict) else s.model_dump() for s in sans])

        serial = self._get_next_serial(db, ca.id)

        validity_days = data.get("validity_days") or settings_svc.get(db, "default_cert_validity_days")

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
            validity_days=validity_days,
            requested_by=user_id,
        )

        if ca.auto_approve:
            self._sign_certificate(cert_record, ca, key_pem, validity_days, user_id)

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
        subject_dn = ", ".join(f"{k}={v}" for k, v in csr_info["subject"].items())
        self._check_duplicate_cn(db, ca.id, subject_dn)
        serial = self._get_next_serial(db, ca.id)

        validity_days = data.get("validity_days") or settings_svc.get(db, "default_cert_validity_days")

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
            validity_days=validity_days,
            requested_by=user_id,
        )

        if ca.auto_approve:
            ca_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)
            cert_pem = crypto.sign_csr(
                data["csr_pem"], ca.certificate_pem, ca_key, validity_days,
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
        if cert.requested_by == user_id:
            raise ValueError("Cannot approve a certificate you requested")
        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == cert.ca_id).first()

        if cert.private_key_encrypted:
            key_pem = decrypt_private_key(cert.private_key_encrypted, settings.PKI_MASTER_KEY)
        else:
            key_pem = None

        ca_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)
        cert_pem = crypto.sign_csr(
            cert.csr_pem, ca.certificate_pem, ca_key, cert.validity_days or 365,
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
        if cert.requested_by == user_id:
            raise ValueError("Cannot deny a certificate you requested")
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
        new_cert = self.request_certificate(db, user_id, data, _skip_duplicate_check=True)
        audit.log(db, user_id, AuditAction.renewed_cert, AuditResourceType.certificate, new_cert.id, {"renewed_from": cert_id})
        return new_cert

    def download(self, cert_id: str, fmt: str, db: Session, passphrase: str | None = None, key_only: bool = False) -> bytes:
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert or not cert.certificate_pem:
            raise ValueError("Certificate not found or not yet issued")

        if key_only:
            if not cert.private_key_encrypted:
                raise ValueError("No private key available for this certificate")
            key_pem = decrypt_private_key(cert.private_key_encrypted, settings.PKI_MASTER_KEY)
            return key_pem.encode() if isinstance(key_pem, str) else key_pem

        key_pem = None
        if cert.private_key_encrypted and fmt == "pkcs12":
            key_pem = decrypt_private_key(cert.private_key_encrypted, settings.PKI_MASTER_KEY)

        return crypto.convert_format(cert.certificate_pem, key_pem, fmt, passphrase=passphrase)
