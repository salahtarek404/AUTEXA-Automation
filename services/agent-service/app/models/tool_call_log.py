from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.session import Base

class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, default="autexa", index=True, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    tool_name = Column(String, index=True)
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
