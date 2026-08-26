from sqlalchemy.orm import Session
from app.models.knowledge_base_chunk import KnowledgeBaseChunk, HAS_PGVECTOR
from app.rag.embeddings import get_query_embedding
import numpy as np

def retrieve_chunks(db: Session, query: str, limit: int = 3, filter_source: str = None) -> list[KnowledgeBaseChunk]:
    """
    Retrieves the most similar knowledge base chunks for a given query.
    If pgvector is installed and enabled, it executes similarity search on the database.
    Otherwise, it fetches and computes cosine similarity in Python as a fallback.
    """
    try:
        query_vector = get_query_embedding(query)
    except Exception as e:
        print(f"Failed to generate query embedding: {e}")
        return []

    stmt = db.query(KnowledgeBaseChunk)
    if filter_source:
        stmt = stmt.filter(KnowledgeBaseChunk.source_doc == filter_source)

    if HAS_PGVECTOR:
        try:
            # Order by cosine distance: <=> operator in pgvector
            stmt = stmt.order_by(KnowledgeBaseChunk.embedding.cosine_distance(query_vector))
            return stmt.limit(limit).all()
        except Exception as db_err:
            print(f"pgvector query failed (might not have extension installed in DB): {db_err}. Falling back to Python similarity.")
            # Fallback to python similarity if the DB query failed

    # Fetch all chunks and calculate similarity in Python
    chunks = stmt.all()
    if not chunks:
        return []

    def cosine_similarity(v1, v2):
        if v1 is None or v2 is None:
            return 0.0
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)

    sorted_chunks = sorted(chunks, key=lambda c: cosine_similarity(c.embedding, query_vector), reverse=True)
    return sorted_chunks[:limit]
