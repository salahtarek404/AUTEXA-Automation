from sqlalchemy import Column, Integer, String, Text, PickleType
from app.db.session import Base
from app.core.config import settings

try:
    if settings.DATABASE_URL.startswith("postgresql"):
        from pgvector.sqlalchemy import Vector
        HAS_PGVECTOR = True
    else:
        HAS_PGVECTOR = False
except Exception:
    HAS_PGVECTOR = False

class KnowledgeBaseChunk(Base):
    __tablename__ = "knowledge_base_chunks"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, default="autexa", index=True, nullable=False)
    source_doc = Column(String, index=True)
    content = Column(Text, nullable=False)
    
    if HAS_PGVECTOR:
        embedding = Column(Vector(3072))  # gemini-embedding-001 is 3072-dimensional
    else:
        # PickleType works on SQLite/PostgreSQL and serializes python list of floats
        embedding = Column(PickleType)
