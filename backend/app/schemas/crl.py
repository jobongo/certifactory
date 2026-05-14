from datetime import datetime

from pydantic import BaseModel


class CRLResponse(BaseModel):
    id: str
    ca_id: str
    crl_pem: str
    this_update: datetime
    next_update: datetime
    crl_number: int
    created_at: datetime

    model_config = {"from_attributes": True}
