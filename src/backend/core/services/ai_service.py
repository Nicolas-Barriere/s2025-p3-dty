""" AI services """
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from openai import OpenAI


class AIService:
    """Service class for AI-related operations."""

    def __init__(self):
        """Ensure that the AI configuration is set properly."""
        if (
            settings.AI_BASE_URL is None
            or settings.AI_API_KEY is None
            or settings.AI_MODEL is None
        ):
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
            raise RuntimeError("AI response does not contain an answer")

        return content
    
    def call_ai_api_with_extra_instructions(self, instructions, prompt):
        """Helper method to call the OpenAI API and process the response."""
        data = {
            "model": settings.AI_MODEL,
            "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": prompt}],
            "stream": False,
            "n": 1,
        }

        response = self.client.chat.completions.create(**data)
        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("AI response does not contain an answer")

        return content
    