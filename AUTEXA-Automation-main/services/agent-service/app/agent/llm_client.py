import google.generativeai as genai
from app.core.config import settings

class GeminiClient:
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-3.5-flash")

    def generate_reply(self, messages: list) -> str:
        # Convert internal message format to Gemini's format if needed.
        # For a simple turn, we can just pass the last user message to start.
        # Phase 1 simple logic: Just grab the last user message.
        last_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
        if not last_message:
            return "Hello! How can I help you today?"
            
        try:
            response = self.model.generate_content(last_message)
            return response.text
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return "I apologize, but I am currently unavailable. Please try again later."

llm_client = GeminiClient()
