"""
Refactored chatbot implementation using Albert API for mail processing operations.

This module provides a clean, modular interface for email processing operations through
function calling and intent detection with a conversation handler.

Author: ANCT
Date: 2025-06-19
Refactored: 2025-06-26
Updated: 2025-07-02
"""

import logging
from typing import Dict, List, Optional, Any

from .config import AlbertConfig
from .api_client import AlbertAPIClient
from .email_processor import EmailProcessor
from .function_executor import FunctionExecutor
from .conversation_handler import ConversationHandler
from .exceptions import ChatbotError

logger = logging.getLogger(__name__)


class AlbertChatbot:
    """
    Refactored chatbot implementation using Albert API for mail processing operations.
    
    This class provides access to the conversation handler for processing user messages
    with function calling. Email-specific operations are delegated to the email_processor.
    """

    def __init__(self, config: Optional[AlbertConfig] = None):
        """
        Initialize the Albert chatbot with modular components.
        
        Args:
            config: Configuration for Albert API. If None, uses default config.
        """
        self.config = config or AlbertConfig()
        
        # Initialize components
        self.api_client = AlbertAPIClient(self.config)
        self.email_processor = EmailProcessor(self.api_client)
        self.function_executor = FunctionExecutor(self.email_processor)
        self.conversation_handler = ConversationHandler(self.api_client, self.function_executor)

    def process_user_message(self, user_message: str, user_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main entry point for processing user messages with function calling.
        
        Args:
            user_message: The user's input message
            user_id: User ID for email operations (optional)
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Dictionary containing the appropriate response based on function calls
        """
        return self.conversation_handler.process_user_message(user_message, user_id, conversation_history)


def get_chatbot(config: Optional[AlbertConfig] = None) -> AlbertChatbot:
    """
    Factory function to get a configured AlbertChatbot instance.
    
    Args:
        config: Optional configuration for Albert API. If None, uses default config.
        
    Returns:
        Configured AlbertChatbot instance
    """
    return AlbertChatbot(config=config)
