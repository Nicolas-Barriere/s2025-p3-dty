"""
Configuration settings for the Albert chatbot.

This module contains configuration classes and settings for the chatbot system.
"""

from dataclasses import dataclass
from enum import Enum

@dataclass
class AlbertConfig:
    """Configuration for Albert API."""
    name: str = "albert-etalab"
    base_url: str = "https://albert.api.etalab.gouv.fr/v1"
    api_key: str = "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0NTQsInRva2VuX2lkIjoxNjM5LCJleHBpcmVzX2F0IjoxNzgxNzMzNjAwfQ.CwVlU_n4uj6zsfxZV1AFLxfwqzd7puYzs4Agp8HhYxs"
    model: str = "albert-large"
    temperature: float = 0.3
    max_tokens: int = 4000  # Increased for better response capacity
    timeout: int = 30
    max_iterations: int = 5
    # RAG-specific settings
    max_emails_per_batch: int = 500  # Limit emails processed per request
    max_email_content_length: int = 10000  # Limit email content size
    batch_upload_delay: float = 1.0  # Delay between batch uploads
    min_relevance_score_percentage: float = 0.8  # Minimum score as percentage of highest score (0.0-1.0)
