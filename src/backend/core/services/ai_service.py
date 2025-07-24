from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from openai import OpenAI

from core.ai.utils import is_ai_enabled


class AIService:
    """Service class for AI-related operations."""

    def __init__(self):
        """Ensure that the AI configuration is set properly."""
        if not is_ai_enabled():
            raise ImproperlyConfigured("AI configuration not set")
        self.client = OpenAI(base_url=settings.AI_BASE_URL, api_key=settings.AI_API_KEY)

    def call_ai_api(self, prompt):
        """Helper method to call the OpenAI API and process the response."""
        data = {
            "model": settings.AI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "n": 1,
        }

        response = self.client.chat.completions.create(**data)
        content = response.choices[0].message.content

        if not content:
            raise ValueError("AI response does not contain an answer")

        return content
