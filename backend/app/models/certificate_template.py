import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database import Base
from app.models.certificate import CertificateType
from app.models.certificate_authority import KeyAlgorithm


class CertificateTemplate(Base):
    __tablename__ = "certificate_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ca_id: Mapped[str] = mapped_column(String(36), ForeignKey("certificate_authorities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[CertificateType] = mapped_column(Enum(CertificateType), default=CertificateType.server)
    key_algorithm: Mapped[KeyAlgorithm] = mapped_column(Enum(KeyAlgorithm), default=KeyAlgorithm.RSA)
    key_size: Mapped[int] = mapped_column(Integer, default=2048)
    validity_days: Mapped[int] = mapped_column(Integer, default=365)
    key_usage: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extended_key_usage: Mapped[list | None] = mapped_column(JSON, nullable=True)
    custom_extensions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    subject_defaults: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    ca = relationship("CertificateAuthority", backref="templates")
