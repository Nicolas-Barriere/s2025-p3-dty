"""
Chatbot module for mail processing operations using Albert API.
"""

from .chatbot import (
    AlbertChatbot,
    AlbertConfig,
    MailClassification,
    get_chatbot,
)

__all__ = [
    "AlbertChatbot",
    "AlbertConfig", 
    "MailClassification",
    "get_chatbot",
]
