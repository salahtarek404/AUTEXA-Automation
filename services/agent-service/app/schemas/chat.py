from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    channel: str
    sender_id: str
    message: str
    tenant_id: Optional[str] = "autexa"
    # Optional merge hints for cross-channel identity resolution (Phase 4).
    # If provided, will be used to match against an existing lead by phone or
    # email across channels. Only exact matches trigger a merge.
    phone: Optional[str] = None
    email: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
