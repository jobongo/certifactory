from datetime import datetime
from pydantic import BaseModel


class ApiTokenCreate(BaseModel):
    name: str


class ApiTokenResponse(BaseModel):
    id: str
    name: str
    token_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenCreated(BaseModel):
    id: str
    name: str
    token: str
    token_prefix: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenListResponse(BaseModel):
    items: list[ApiTokenResponse]
