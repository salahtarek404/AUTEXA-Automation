from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    tenant_id = Column(String, primary_key=True, index=True) # e.g. "autexa", "restaurant", "real_estate", "ecommerce"
    name = Column(String, nullable=False)
    
    # WhatsApp Credentials
    whatsapp_verify_token = Column(String, nullable=True)
    whatsapp_access_token = Column(String, nullable=True)
    whatsapp_phone_number_id = Column(String, nullable=True)

    # Instagram Credentials
    instagram_verify_token = Column(String, nullable=True)
    instagram_access_token = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
