from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CAStatus, Certificate, CertificateAuthority, CertificateRevocationList, CertificateStatus
from app.models.audit_log import AuditLog
from app.services.crl_service import CRLService
from app.services.settings_service import SettingsService

crl_service = CRLService()
settings_service = SettingsService()


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


def cleanup_audit_logs():
    db: Session = SessionLocal()
    try:
        retention_days = settings_service.get(db, "audit_retention_days")
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        db.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
        db.commit()
    finally:
        db.close()


def get_crl_interval_minutes():
    db: Session = SessionLocal()
    try:
        return settings_service.get(db, "crl_regen_interval_minutes")
    finally:
        db.close()
