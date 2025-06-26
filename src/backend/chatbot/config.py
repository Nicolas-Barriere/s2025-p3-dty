"""
Configuration settings for the Albert chatbot.

This module contains configuration classes and settings for the chatbot system.
"""

from dataclasses import dataclass
from enum import Enum


class MailClassification(Enum):
    """Mail classification categories."""
    URGENT = "urgent"
    NORMAL = "normal"
    LOW_PRIORITY = "low_priority"
    SPAM = "spam"
    INFORMATION = "information"
    REQUEST = "request"
    COMPLAINT = "complaint"
    SUPPORT = "support"


@dataclass
class AlbertConfig:
    """Configuration for Albert API."""
    name: str = "albert-etalab"
    base_url: str = "https://albert.api.etalab.gouv.fr/v1"
    api_key: str = "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0NTQsInRva2VuX2lkIjoxNjM5LCJleHBpcmVzX2F0IjoxNzgxNzMzNjAwfQ.CwVlU_n4uj6zsfxZV1AFLxfwqzd7puYzs4Agp8HhYxs"
    model: str = "albert-large"
    temperature: float = 0.3
    max_tokens: int = 1000
    timeout: int = 30
    max_iterations: int = 5
