import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AcmeAccount(Base):
    __tablename__ = "acme_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    jwk: Mapped[dict] = mapped_column(JSON, nullable=False)
    jwk_thumbprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    contact: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class AcmeOrder(Base):
    __tablename__ = "acme_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("acme_accounts.id"), nullable=False)
    ca_id: Mapped[str] = mapped_column(String(36), ForeignKey("certificate_authorities.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    identifiers: Mapped[list] = mapped_column(JSON, nullable=False)
    not_before: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    not_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    certificate_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("certificates.id"), nullable=True)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AcmeAuthorization(Base):
    __tablename__ = "acme_authorizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("acme_orders.id"), nullable=False)
    identifier_type: Mapped[str] = mapped_column(String(20), default="dns")
    identifier_value: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    challenges: Mapped[list] = mapped_column(JSON, nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
