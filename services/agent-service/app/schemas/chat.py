from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    channel: str
    sender_id: str
    message: str
    tenant_id: Optional[str] = "autexa"

class ChatResponse(BaseModel):
    reply: str
