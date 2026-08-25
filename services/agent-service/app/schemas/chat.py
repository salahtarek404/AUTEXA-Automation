from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    channel: str
    sender_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str
