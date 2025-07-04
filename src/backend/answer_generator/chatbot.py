"""
Simplified chatbot implementation for email response generation.

This module provides a minimal interface for generating email responses.
"""

import logging
import re
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SimpleChatbot:
    """
    Simple chatbot implementation for generating email responses.
    """
    
    def __init__(self):
        """Initialize the chatbot."""
        self.api_key = None  # Replace with actual API key configuration if needed
    
    def _extract_subject(self, message: str) -> str:
        """
        Extract the email subject from the message.
        
        Args:
            message: The message text that may contain a subject line
            
        Returns:
            The extracted subject or empty string
        """
        subject = ""
        if "Sujet:" in message:
            subject_start = message.find("Sujet:") + 7
            subject_end = message.find("\n", subject_start)
            if subject_end > subject_start:
                subject = message[subject_start:subject_end].strip()
        return subject
    
    def _extract_key_points(self, message: str) -> List[str]:
        """
        Extract potential key points from the email content.
        
        Args:
            message: The full message text
            
        Returns:
            List of identified key points
        """
        # Get email body after the subject
        body = ""
        if "Sujet:" in message:
            body_start = message.find("\n", message.find("Sujet:"))
            if body_start > 0:
                body = message[body_start:].strip()
        else:
            body = message
        
        # Simple heuristic to identify potential questions or requests
        sentences = re.split(r'[.!?]+', body)
        key_points = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Look for questions
            if '?' in sentence or sentence.lower().startswith(('pourriez-vous', 'pouvez-vous', 'est-ce que', 'comment', 'quand', 'pourquoi')):
                key_points.append(sentence)
            # Look for requests or important statements
            elif any(word in sentence.lower() for word in ['besoin', 'demande', 'nécessaire', 'important', 'urgent', 'merci de', 'prière de']):
                key_points.append(sentence)
        
        # Limit to top 3 key points
        return key_points[:3]
    
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
            # Extract email subject and key points
            subject = self._extract_subject(message)
            key_points = self._extract_key_points(message)
            
            logger.info(f"Generating response for email with subject: '{subject}'")
            if key_points:
                logger.info(f"Identified key points: {key_points}")
            
            # Create a more personalized and contextual response
            greeting = "Bonjour,"
            
            # Build the body based on subject and key points
            body_parts = []
            
            # Subject acknowledgment
            if subject:
                body_parts.append(f"Merci pour votre message concernant \"{subject}\".")
            else:
                body_parts.append("Merci pour votre message.")
            
            # Acknowledgment of key points
            if key_points:
                body_parts.append("J'ai bien pris note de votre demande.")
                
                # If there are specific questions/requests, acknowledge them
                if len(key_points) == 1:
                    body_parts.append("Concernant votre point sur : \"" + key_points[0] + "\", nous allons l'examiner avec attention.")
                else:
                    points_acknowledgment = "J'ai bien noté vos différents points et nous allons les traiter avec attention."
                    body_parts.append(points_acknowledgment)
            
            # Standard response content
            body_parts.append("Nous mettrons tout en œuvre pour vous apporter une réponse complète dans les meilleurs délais.")
            
            # Closing
            closing = """
N'hésitez pas à nous contacter pour toute information complémentaire.

Cordialement,
L'équipe DTY
"""
            
            # Combine all parts into the final response
            response = greeting + "\n\n" + "\n".join(body_parts) + "\n\n" + closing
            
            return {
                'success': True,
                'response': response.strip(),
                'type': 'email_response'
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "Je suis désolé, une erreur s'est produite lors de la génération de la réponse."
            }


# Singleton instance
_chatbot_instance = None

def get_chatbot() -> SimpleChatbot:
    """
    Get the chatbot instance (singleton pattern).
    
    Returns:
        SimpleChatbot instance
    """
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = SimpleChatbot()
    return _chatbot_instance
