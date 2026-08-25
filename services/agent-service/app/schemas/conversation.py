from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from .lead import Lead

class ConversationBase(BaseModel):
    lead_id: Optional[int] = None
    channel: str
    messages: List[Dict[str, Any]] = []
    ai_summary: Optional[str] = None

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: int
    created_at: datetime
    lead: Optional[Lead] = None

    model_config = {"from_attributes": True}
