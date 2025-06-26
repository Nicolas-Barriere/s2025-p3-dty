"""
Refactored chatbot implementation using Albert API for mail processing operations.

This module provides a clean, modular interface for email processing operations:
- Mail summarization
- Mail answer generation  
- Mail classification
- Conversational AI with function calling
- Multi-step email operations

Author: ANCT
Date: 2025-06-19
Refactored: 2025-06-26
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
    
    This is the main interface class that orchestrates various components:
    - API communication via AlbertAPIClient
    - Email processing via EmailProcessor
    - Function execution via FunctionExecutor
    - Conversation handling via ConversationHandler
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

    # Main interface methods delegating to modular components
    
    def summarize_mail(self, mail_content: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
        """
        Summarize an email content using Albert API.
        
        Args:
            mail_content: The content of the email to summarize
            sender: Email sender (optional)
            subject: Email subject (optional)
            
        Returns:
            Dictionary containing the summary and metadata
        """
        return self.email_processor.summarize_mail(mail_content, sender, subject)

    def generate_mail_answer(
        self, 
        original_mail: str, 
        context: str = "",
        tone: str = "professional",
        language: str = "french"
    ) -> Dict[str, Any]:
        """
        Generate an answer to an email using Albert API.
        
        Args:
            original_mail: The original email content to respond to
            context: Additional context for the response
            tone: Tone of the response (professional, friendly, formal)
            language: Language for the response
            
        Returns:
            Dictionary containing the generated response and metadata
        """
        return self.email_processor.generate_mail_answer(original_mail, context, tone, language)

    def classify_mail(
        self, 
        mail_content: str, 
        sender: str = "", 
        subject: str = "",
        custom_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Classify an email into categories using Albert API.
        
        Args:
            mail_content: The content of the email to classify
            sender: Email sender (optional)
            subject: Email subject (optional)
            custom_categories: Custom classification categories (optional)
            
        Returns:
            Dictionary containing the classification results
        """
        return self.email_processor.classify_mail(mail_content, sender, subject, custom_categories)

    def process_mail_batch(self, mails: List[Dict[str, str]], operation: str = "summarize") -> List[Dict[str, Any]]:
        """
        Process multiple mails in batch.
        
        Args:
            mails: List of mail dictionaries with 'content', 'sender', 'subject' keys
            operation: Operation to perform ('summarize', 'classify', or 'answer')
            
        Returns:
            List of processed results
        """
        results = []
        
        logger.info(f"Processing batch of {len(mails)} mails for operation: {operation}")
        
        for i, mail in enumerate(mails):
            try:
                mail_content = mail.get('content', '')
                sender = mail.get('sender', '')
                subject = mail.get('subject', '')
                
                if operation == "summarize":
                    result = self.summarize_mail(mail_content, sender, subject)
                elif operation == "classify":
                    result = self.classify_mail(mail_content, sender, subject)
                elif operation == "answer":
                    context = mail.get('context', '')
                    tone = mail.get('tone', 'professional')
                    result = self.generate_mail_answer(mail_content, context, tone)
                else:
                    result = {'success': False, 'error': f'Unknown operation: {operation}'}
                
                result['batch_index'] = i
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing mail {i} in batch: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'batch_index': i
                })
        
        logger.info(f"Completed batch processing: {len(results)} results")
        return results

    def chat_conversation(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Handle conversational chat with the user.
        
        Args:
            user_message: The user's message
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Dictionary containing the conversational response
        """
        return self.conversation_handler.chat_conversation(user_message, conversation_history)

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

    # Legacy method names for backward compatibility
    def _make_request(self, messages: List[Dict[str, str]], functions: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Legacy method - delegates to API client."""
        return self.api_client.make_request(messages, functions)
    
    def _get_email_tools(self) -> List[Dict[str, Any]]:
        """Legacy method - delegates to tools definition."""
        from .tools import EmailToolsDefinition
        return EmailToolsDefinition.get_email_tools()
    
    def _execute_email_function(self, function_name: str, arguments: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Legacy method - delegates to function executor."""
        return self.function_executor.execute_function(function_name, arguments, user_id)


def get_chatbot(config: Optional[AlbertConfig] = None) -> AlbertChatbot:
    """
    Factory function to get a configured AlbertChatbot instance.
    
    Args:
        config: Optional configuration for Albert API. If None, uses default config.
        
    Returns:
        Configured AlbertChatbot instance
    """
    return AlbertChatbot(config=config)
