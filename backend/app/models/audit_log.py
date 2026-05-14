import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database import Base


class AuditAction(str, enum.Enum):
    created_ca = "created_ca"
    issued_cert = "issued_cert"
    revoked_cert = "revoked_cert"
    approved_request = "approved_request"
    denied_request = "denied_request"
    login = "login"
    logout = "logout"
    config_change = "config_change"
    downloaded_cert = "downloaded_cert"
    created_user = "created_user"
    updated_user = "updated_user"
    generated_crl = "generated_crl"
    renewed_cert = "renewed_cert"
    submitted_csr = "submitted_csr"


class AuditResourceType(str, enum.Enum):
    ca = "ca"
    certificate = "certificate"
    user = "user"
    crl = "crl"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    resource_type: Mapped[AuditResourceType] = mapped_column(Enum(AuditResourceType), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
