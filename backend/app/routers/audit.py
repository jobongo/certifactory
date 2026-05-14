import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_role
from app.models import AuditLog, AuditAction, AuditResourceType, User, UserRole
from app.schemas.audit import AuditLogListResponse

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

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
    items = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
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
    writer.writerow(["id", "user_id", "action", "resource_type", "resource_id", "ip_address", "created_at"])
    for log in logs:
        writer.writerow([log.id, log.user_id, log.action.value, log.resource_type.value, log.resource_id, log.ip_address, log.created_at])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit_logs.csv"})
