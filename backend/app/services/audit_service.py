from sqlalchemy.orm import Session
from app.models import AuditAction, AuditLog, AuditResourceType

class AuditService:
    def log(self, db: Session, user_id: str, action: AuditAction, resource_type: AuditResourceType, resource_id: str, details: dict | None = None, ip_address: str | None = None) -> AuditLog:
        entry = AuditLog(user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id, details=details, ip_address=ip_address)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
