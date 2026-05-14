import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CertificateRevocationList(Base):
    __tablename__ = "certificate_revocation_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ca_id: Mapped[str] = mapped_column(String(36), ForeignKey("certificate_authorities.id"), nullable=False)
    crl_pem: Mapped[str] = mapped_column(Text, nullable=False)
    this_update: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    next_update: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    crl_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    ca = relationship("CertificateAuthority", backref="crls")
