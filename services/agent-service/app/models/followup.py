from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base


class Followup(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    type = Column(String, default="auto_message")  # auto_message / reminder
    channel = Column(String, nullable=False)  # website / whatsapp
    status = Column(String, default="pending")  # pending / sent / skipped
    created_at = Column(DateTime(timezone=True), server_default=func.now())
