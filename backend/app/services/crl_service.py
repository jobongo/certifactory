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
