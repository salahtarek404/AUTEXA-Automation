from google import genai
from google.genai import types
from app.core.config import settings

# Configure Gemini API with new SDK
_client = genai.Client(api_key=settings.GEMINI_API_KEY)

def get_embedding(text: str) -> list[float]:
    """Generates embedding for a document chunk using Gemini's embedding model."""
    try:
        response = _client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Error generating document embedding: {e}")
        raise e

def get_query_embedding(text: str) -> list[float]:
    """Generates embedding for a query using Gemini's embedding model."""
    try:
        response = _client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        raise e
