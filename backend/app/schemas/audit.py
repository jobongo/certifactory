from datetime import datetime
from pydantic import BaseModel

class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    details: dict | None
    ip_address: str | None
    created_at: datetime
    model_config = {"from_attributes": True}

class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    per_page: int
