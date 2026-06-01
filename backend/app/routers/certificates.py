from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
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
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])
cert_service = CertificateService()
import_service = ImportService()


@router.get("", response_model=CertificateListResponse)
def list_certificates(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    ca_id: str | None = None,
    cert_status: str | None = Query(None, alias="status"),
    search: str | None = None,
    sort_by: str = Query("created_at", pattern="^(subject_dn|type|status|not_after|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor, UserRole.requester)),
):
    query = db.query(Certificate)
    if current_user.role == UserRole.requester:
        query = query.filter(Certificate.requested_by == current_user.id)
    if ca_id:
        query = query.filter(Certificate.ca_id == ca_id)
    if cert_status:
        query = query.filter(Certificate.status == CertificateStatus(cert_status))
    if search:
        query = query.filter(Certificate.subject_dn.ilike(f"%{search}%"))
    total = query.count()
    sort_col = getattr(Certificate, sort_by)
    order = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    items = query.order_by(order).offset((page - 1) * per_page).limit(per_page).all()
    return CertificateListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
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


@router.delete("/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if cert.status == CertificateStatus.active:
        raise HTTPException(status_code=400, detail="Cannot delete an active certificate. Revoke it first.")
    from app.models import AuditAction, AuditResourceType
    from app.services.audit_service import AuditService
    cert_dn = cert.subject_dn
    db.delete(cert)
    db.commit()
    AuditService().log(db, current_user.id, AuditAction.revoked_cert, AuditResourceType.certificate, cert_id, {"name": cert_dn, "action": "deleted"})


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
    format: str = Query("pem", pattern="^(pem|der|pkcs12)$"),
    passphrase: str | None = None,
    key_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.requester)),
):
    try:
        data = cert_service.download(cert_id, format, db, passphrase=passphrase, key_only=key_only)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if key_only:
        return Response(
            content=data,
            media_type="application/x-pem-file",
            headers={"Content-Disposition": "attachment; filename=private_key.pem"},
        )

    media_types = {"pem": "application/x-pem-file", "der": "application/x-x509-ca-cert", "pkcs12": "application/x-pkcs12"}
    extensions = {"pem": "pem", "der": "der", "pkcs12": "p12"}

    return Response(
        content=data,
        media_type=media_types[format],
        headers={"Content-Disposition": f"attachment; filename=certificate.{extensions[format]}"},
    )
