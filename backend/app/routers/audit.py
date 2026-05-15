import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_role
from app.models import AuditLog, AuditAction, AuditResourceType, User, UserRole
from app.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _enrich_log(log, db):
    user = db.query(User).filter(User.id == log.user_id).first()
    resource_name = None
    if log.details:
        resource_name = log.details.get("name") or log.details.get("subject_dn")
    return AuditLogResponse(
        id=log.id,
        user_id=log.user_id,
        username=user.username if user else None,
        action=log.action.value if hasattr(log.action, 'value') else log.action,
        resource_type=log.resource_type.value if hasattr(log.resource_type, 'value') else log.resource_type,
        resource_id=log.resource_id,
        resource_name=resource_name,
        details=log.details,
        ip_address=log.ip_address,
        created_at=log.created_at,
    )


@router.get("/logs", response_model=AuditLogListResponse)
def list_audit_logs(page: int = Query(1, ge=1), per_page: int = Query(25, ge=1, le=100), action: str | None = None, user_id: str | None = None, resource_type: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin, UserRole.auditor, UserRole.operator))):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == AuditAction(action))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == AuditResourceType(resource_type))
    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    items = [_enrich_log(log, db) for log in logs]
    return AuditLogListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/logs/export")
def export_audit_logs(action: str | None = None, user_id: str | None = None, resource_type: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin, UserRole.auditor))):
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
    writer.writerow(["id", "user_id", "username", "action", "resource_type", "resource_id", "resource_name", "ip_address", "created_at"])
    for log in logs:
        enriched = _enrich_log(log, db)
        writer.writerow([enriched.id, enriched.user_id, enriched.username, enriched.action, enriched.resource_type, enriched.resource_id, enriched.resource_name, enriched.ip_address, enriched.created_at])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit_logs.csv"})
