import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database import Base
from app.models.certificate_authority import KeyAlgorithm


class CertificateStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    revoked = "revoked"
    expired = "expired"
    denied = "denied"


class CertificateType(str, enum.Enum):
    server = "server"
    client = "client"
    custom = "custom"


class RevocationReason(str, enum.Enum):
    key_compromise = "key_compromise"
    ca_compromise = "ca_compromise"
    affiliation_changed = "affiliation_changed"
    superseded = "superseded"
    cessation_of_operation = "cessation_of_operation"
    certificate_hold = "certificate_hold"
    unspecified = "unspecified"


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ca_id: Mapped[str] = mapped_column(String(36), ForeignKey("certificate_authorities.id"), nullable=False)
    status: Mapped[CertificateStatus] = mapped_column(Enum(CertificateStatus), default=CertificateStatus.pending)
    type: Mapped[CertificateType] = mapped_column(Enum(CertificateType), nullable=False)
    private_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    csr_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_algorithm: Mapped[KeyAlgorithm] = mapped_column(Enum(KeyAlgorithm), nullable=False)
    key_size: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_dn: Mapped[str] = mapped_column(String(1024), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False)
    san: Mapped[list | None] = mapped_column(JSON, nullable=True)
    not_before: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    not_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    key_usage: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extended_key_usage: Mapped[list | None] = mapped_column(JSON, nullable=True)
    custom_extensions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    validity_days: Mapped[int] = mapped_column(Integer, default=365)
    revocation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revocation_reason: Mapped[RevocationReason | None] = mapped_column(Enum(RevocationReason), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    ca = relationship("CertificateAuthority", backref="certificates")
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])

    @property
    def has_private_key(self) -> bool:
        return self.private_key_encrypted is not None
