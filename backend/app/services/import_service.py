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
