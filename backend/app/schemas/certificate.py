from datetime import datetime

from pydantic import BaseModel

from app.schemas.ca import SubjectDN


class SANEntry(BaseModel):
    type: str
    value: str


class CertificateCreate(BaseModel):
    ca_id: str
    subject: SubjectDN
    san: list[SANEntry] | None = None
    type: str = "server"
    key_algorithm: str = "RSA"
    key_size: int = 2048
    validity_days: int = 365
    key_usage: list[str] | None = None
    extended_key_usage: list[str] | None = None
    custom_extensions: list[dict] | None = None


class CSRSubmit(BaseModel):
    ca_id: str
    csr_pem: str
    type: str = "server"
    validity_days: int = 365
    key_usage: list[str] | None = None
    extended_key_usage: list[str] | None = None


class CertificateRevoke(BaseModel):
    reason: str = "unspecified"


class CertificateResponse(BaseModel):
    id: str
    ca_id: str
    status: str
    type: str
    certificate_pem: str | None
    csr_pem: str | None
    key_algorithm: str
    key_size: int
    subject_dn: str
    serial_number: str
    san: list | None
    not_before: datetime | None
    not_after: datetime | None
    key_usage: list | None
    extended_key_usage: list | None
    revocation_date: datetime | None
    revocation_reason: str | None
    requested_by: str
    approved_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CertificateListResponse(BaseModel):
    items: list[CertificateResponse]
    total: int
    page: int
    per_page: int
