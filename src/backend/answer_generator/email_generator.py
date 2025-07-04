"""
Enhanced chatbot implementation for email response generation.

This module provides an interface for generating email responses using Albert API.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any

from answer_generator.api_client import AlbertAPIClient
from answer_generator.config import AlbertConfig
from answer_generator.exceptions import AlbertAPIError
from answer_generator.email_retrieval import get_parsed_message_content

logger = logging.getLogger(__name__)


class EmailGenerator:
    """
    Enhanced chatbot implementation for generating email responses using Albert API.
    """
    
    def __init__(self):
        """Initialize the chatbot with Albert API client."""
        self.config = AlbertConfig()
        self.api_client = AlbertAPIClient(self.config)
  
    
    def generate_response_with_albert(self, 
        original_mail: str, 
        context: str = "",
        tone: str = "professional",
        language: str = "french") -> Dict[str, Any]:
        """
        Generate a response using Albert API.
        
        Args:
            message: The email content to respond to
            sender: Email sender
            subject: Email subject
            tone: Tone of the response (professional, friendly, formal)
            
        Returns:
            Dictionary with the generated response and metadata
        """
        try:
            logger.info(f"Generating mail answer with tone: {tone}")
            
            functions = [{
                "name": "generate_email_response",
                "description": "Génère une réponse professionnelle à un email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "Réponse complète à l'email"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Sujet proposé pour la réponse"
                        },
                        "tone_used": {
                            "type": "string",
                            "description": "Ton utilisé dans la réponse"
                        },
                        "estimated_reading_time": {
                            "type": "integer",
                            "description": "Temps de lecture estimé en secondes"
                        }
                    },
                    "required": ["response", "subject", "tone_used"]
                }
            }]
            
            system_prompt = f"""
            Tu es un assistant de rédaction d'emails professionnel. 
            Tu DOIS utiliser la fonction generate_email_response pour générer des réponses aux emails.
            Ne réponds jamais directement sans utiliser cette fonction.
            
            Génère des réponses appropriées en {language} avec un ton {tone}.
            Assure-toi que tes réponses sont:
            - Claires et concises
            - Respectueuses et professionnelles
            - Adaptées au contexte
            - Bien structurées
            """
            
            user_prompt = f"""
            Utilise la fonction generate_email_response pour générer une réponse à cet email:
            
            Email original:
            {original_mail}
            
            Contexte supplémentaire:
            {context}
            
            Ton souhaité: {tone}
            Langue: {language}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.api_client.make_request(messages, functions)
            
            result = self._process_response(response, 'answer', context, tone)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating mail answer: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': {'response': 'Erreur lors de la génération de la réponse.'}
            }


    def process_user_message(self, message: str, user_id: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            message: The user's message text
            user_id: The ID of the user
            conversation_history: Optional list of previous messages
            
        Returns:
            Dictionary with response information
        """
        try:
            # Extract email subject and sender
            subject = self._extract_subject(message)
            sender = self._extract_sender(message)
            key_points = self._extract_key_points(message)
            
            logger.info(f"Processing email from {sender} with subject: '{subject}'")
            if key_points:
                logger.info(f"Identified key points: {key_points}")
            
            # Try to generate response with Albert API
            try:
                response = self.generate_response_with_albert(
                    original_mail=message,
                    tone="professional",
                    language="french"
                )
                if response.get('success', False):
                    return response
            except Exception as api_error:
                logger.error(f"Failed to generate response with Albert API: {api_error}")
                # Continue to fallback method if API fails
            
            # Fallback to the built-in generation method
            return self._generate_fallback_response(subject, key_points)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "Je suis désolé, une erreur s'est produite lors de la génération de la réponse."
            }
    
    def process_retrieved_email(self, message_id: str, user_id: str) -> Dict[str, Any]:
        """
        Process an email retrieved by its ID and generate a response.
        
        Args:
            message_id: UUID of the message to process
            user_id: UUID of the user requesting the processing
            
        Returns:
            Dictionary with response information
        """
        try:
            # Retrieve the email content
            email_data = get_parsed_message_content(message_id, user_id)
            
            if not email_data:
                logger.error(f"Failed to retrieve email {message_id}: Email not found or content could not be retrieved")
                return {
                    'success': False,
                    'error': 'Failed to retrieve email',
                    'response': "Je suis désolé, je n'ai pas pu récupérer cet email."
                }
            
            # Now process the email content
            subject = email_data.get('subject', '(Pas de sujet)')
            logger.info(f"Processing retrieved email with subject: '{subject}'")
            
            # Extract sender information
            sender_info = email_data.get('sender', {})
            sender_name = sender_info.get('name', '')
            sender_email = sender_info.get('email', '')
            
            # Get the message content (prefer text_body over html_body)
            message_body = email_data.get('text_body', '')
            if not message_body:
                message_body = email_data.get('html_body', '(Contenu vide)')
            
            # Construct the email content in the format expected by generate_response_with_albert
            formatted_email = f"""
            Sujet: {subject}
            
            De: {sender_name} <{sender_email}>
            
            {message_body}
            """
            
            # Try to generate response with Albert API
            try:
                response = self.generate_response_with_albert(
                    original_mail=formatted_email,
                    tone="professional",
                    language="french"
                )
                if response.get('success', False):
                    return response
            except Exception as api_error:
                logger.error(f"Failed to generate response with Albert API: {api_error}")
                # Continue to fallback method if API fails
            
            # Extract key points for fallback method
            key_points = self._extract_key_points(formatted_email)
            
            # Fallback to the built-in generation method
            return self._generate_fallback_response(subject, key_points)
            
        except Exception as e:
            logger.error(f"Error processing retrieved email: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "Je suis désolé, une erreur s'est produite lors du traitement de cet email."
            }
    

# Singleton instance
_generator_instance = None

def get_email_generator() -> EmailGenerator:
    """
    Get the generator instance (singleton pattern).
    
    Returns:
        EmailGenerator instance
    """
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = EmailGenerator()
    return _generator_instance
