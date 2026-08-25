from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LeadBase(BaseModel):
    name: str
    phone: Optional[str] = None
    instagram_handle: Optional[str] = None
    email: Optional[str] = None
    source: str
    business_type: Optional[str] = None
    service_requested: Optional[str] = None
    intent: Optional[str] = None
    priority: Optional[str] = None
    budget_estimate: Optional[str] = None
    status: Optional[str] = "new"

class LeadCreate(LeadBase):
    pass

class Lead(LeadBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
