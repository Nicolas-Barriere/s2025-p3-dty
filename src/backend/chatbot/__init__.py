"""
Chatbot module for mail processing operations using Albert API.
"""

from .chatbot import AlbertChatbot, get_chatbot
from .config import AlbertConfig, MailClassification

__all__ = [
    "AlbertChatbot",
    "AlbertConfig", 
    "MailClassification",
    "get_chatbot",
]
