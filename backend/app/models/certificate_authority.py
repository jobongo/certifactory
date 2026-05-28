import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CAType(str, enum.Enum):
    root = "root"
    intermediate = "intermediate"


class CAStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    expired = "expired"
    revoked = "revoked"


class KeyAlgorithm(str, enum.Enum):
    RSA = "RSA"
    EC = "EC"


class OCSPSigningMode(str, enum.Enum):
    ca_key = "ca_key"
    dedicated_cert = "dedicated_cert"


class CertificateAuthority(Base):
    __tablename__ = "certificate_authorities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[CAType] = mapped_column(Enum(CAType), nullable=False)
    status: Mapped[CAStatus] = mapped_column(Enum(CAStatus), default=CAStatus.active)
    parent_ca_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("certificate_authorities.id"), nullable=True
    )
    private_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    certificate_pem: Mapped[str] = mapped_column(Text, nullable=False)
    key_algorithm: Mapped[KeyAlgorithm] = mapped_column(Enum(KeyAlgorithm), nullable=False)
    key_size: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_dn: Mapped[str] = mapped_column(String(1024), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False)
    not_before: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    not_after: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    max_path_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    crl_regen_interval_hours: Mapped[int] = mapped_column(Integer, default=24)
    ocsp_signing_mode: Mapped[OCSPSigningMode] = mapped_column(
        Enum(OCSPSigningMode), default=OCSPSigningMode.ca_key
    )
    ocsp_signing_cert_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocsp_signing_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    crl_distribution_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ocsp_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mcp_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    mcp_allowed_operations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    parent = relationship("CertificateAuthority", remote_side="CertificateAuthority.id", backref="children")
    creator = relationship("User", foreign_keys=[created_by])
