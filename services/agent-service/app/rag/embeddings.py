import google.generativeai as genai
from app.core.config import settings

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)

def get_embedding(text: str) -> list[float]:
    """Generates embedding for a document chunk using Gemini's embedding model."""
    try:
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating document embedding: {e}")
        raise e

def get_query_embedding(text: str) -> list[float]:
    """Generates embedding for a query using Gemini's embedding model."""
    try:
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        raise e
