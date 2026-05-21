from datetime import datetime

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    description: str | None = None
    type: str = "server"
    key_algorithm: str = "RSA"
    key_size: int = 2048
    validity_days: int = 365
    key_usage: list[str] | None = None
    extended_key_usage: list[str] | None = None
    custom_extensions: list[dict] | None = None
    subject_defaults: dict | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    key_algorithm: str | None = None
    key_size: int | None = None
    validity_days: int | None = None
    key_usage: list[str] | None = None
    extended_key_usage: list[str] | None = None
    custom_extensions: list[dict] | None = None
    subject_defaults: dict | None = None


class TemplateResponse(BaseModel):
    id: str
    ca_id: str
    name: str
    description: str | None
    type: str
    key_algorithm: str
    key_size: int
    validity_days: int
    key_usage: list | None
    extended_key_usage: list | None
    custom_extensions: list | None
    subject_defaults: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
