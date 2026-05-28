from datetime import datetime

from pydantic import BaseModel


class SubjectDN(BaseModel):
    CN: str
    O: str | None = None
    OU: str | None = None
    C: str | None = None
    ST: str | None = None
    L: str | None = None


class CACreate(BaseModel):
    name: str
    description: str | None = None
    subject: SubjectDN
    key_algorithm: str = "RSA"
    key_size: int = 2048
    validity_days: int = 3650
    max_path_length: int | None = None
    auto_approve: bool = False
    crl_distribution_url: str | None = None
    ocsp_url: str | None = None


class CAUpdate(BaseModel):
    description: str | None = None
    auto_approve: bool | None = None
    ocsp_signing_mode: str | None = None
    crl_distribution_url: str | None = None
    ocsp_url: str | None = None
    crl_regen_interval_hours: int | None = None
    mcp_enabled: bool | None = None
    mcp_allowed_operations: list[str] | None = None


class CAResponse(BaseModel):
    id: str
    name: str
    description: str | None
    type: str
    status: str
    parent_ca_id: str | None
    certificate_pem: str
    key_algorithm: str
    key_size: int
    subject_dn: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    max_path_length: int | None
    auto_approve: bool
    crl_regen_interval_hours: int
    ocsp_signing_mode: str
    crl_distribution_url: str | None
    ocsp_url: str | None
    mcp_enabled: bool
    mcp_allowed_operations: list[str] | None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CATreeNode(BaseModel):
    id: str
    name: str
    type: str
    status: str
    subject_dn: str
    not_after: str
    children: list["CATreeNode"] = []


class CAListResponse(BaseModel):
    items: list[CAResponse]
    total: int
    page: int
    per_page: int
