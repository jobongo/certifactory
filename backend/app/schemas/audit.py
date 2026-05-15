from datetime import datetime
from pydantic import BaseModel

class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    username: str | None = None
    action: str
    resource_type: str
    resource_id: str
    resource_name: str | None = None
    details: dict | None
    ip_address: str | None
    created_at: datetime
    model_config = {"from_attributes": True}

class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    per_page: int
