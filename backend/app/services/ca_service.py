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
