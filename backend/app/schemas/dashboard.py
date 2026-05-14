from pydantic import BaseModel

from app.schemas.certificate import CertificateResponse


class DashboardStats(BaseModel):
    active_cas: int
    active_certs: int
    pending_requests: int
    expiring_soon: int


class ExpiringCertsResponse(BaseModel):
    items: list[CertificateResponse]
