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
