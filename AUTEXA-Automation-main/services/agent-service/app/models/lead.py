from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, default="autexa", index=True, nullable=False)
    name = Column(String, index=True)
    phone = Column(String, nullable=True)
    instagram_handle = Column(String, nullable=True)
    email = Column(String, nullable=True)
    source = Column(String)  # whatsapp/instagram/website/facebook
    business_type = Column(String, nullable=True)
    service_requested = Column(String, nullable=True)
    intent = Column(String, nullable=True)  # buying/browsing/support
    priority = Column(String, nullable=True)  # hot/warm/cold
    budget_estimate = Column(String, nullable=True)
    status = Column(String, default="new")  # new/qualified/proposal_sent/won/lost
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
