"""
Email processing operations using Albert API.

This module provides core email processing functionality like summarization,
classification, and response generation.
"""

import json
import logging
from typing import Dict, List, Optional, Any

from .api_client import AlbertAPIClient
from .config import MailClassification
from .parsers import ContentParser
from .exceptions import AlbertAPIError

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Handles email processing operations using Albert API."""
    
    def __init__(self, api_client: AlbertAPIClient):
        """
        Initialize the email processor.
        
        Args:
            api_client: Albert API client instance
        """
        self.api_client = api_client
        self.parser = ContentParser()
    
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
        try:
            logger.info(f"Summarizing mail from sender: {sender}")
            
            # Prepare the mail context
            mail_context = f"""
            Expéditeur: {sender}
            Sujet: {subject}
            Contenu: {mail_content}
            """
            
            functions = [{
                "name": "summarize_email",
                "description": "Résume le contenu d'un email en français",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Résumé concis de l'email en français"
                        },
                        "key_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Points clés de l'email"
                        },
                        "action_required": {
                            "type": "boolean",
                            "description": "Indique si une action est requise"
                        },
                        "urgency_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Niveau d'urgence"
                        }
                    },
                    "required": ["summary", "key_points", "action_required", "urgency_level"]
                }
            }]
            
            messages = [
                {
                    "role": "system",
                    "content": "Tu es un assistant IA spécialisé dans l'analyse et le résumé d'emails. "
                              "Tu DOIS utiliser la fonction summarize_email pour analyser le contenu des emails. "
                              "Ne réponds jamais directement sans utiliser cette fonction."
                },
                {
                    "role": "user",
                    "content": f"Utilise la fonction summarize_email pour analyser cet email:\n\n{mail_context}"
                }
            ]
            
            response = self.api_client.make_request(messages, functions)
            
            # Extract function call result or content response
            return self._process_response(response, 'summary', sender, subject)
            
        except Exception as e:
            logger.error(f"Error summarizing mail: {e}")
            return {
                'success': False,
                'error': str(e),
                'summary': {'summary': 'Erreur lors du résumé de l\'email.'}
            }

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
            
            return self._process_response(response, 'answer', context, tone)
            
        except Exception as e:
            logger.error(f"Error generating mail answer: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': {'response': 'Erreur lors de la génération de la réponse.'}
            }

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
        try:
            logger.info(f"Classifying mail from sender: {sender}")
            
            # Use custom categories or default ones
            categories = custom_categories or [cat.value for cat in MailClassification]
            
            mail_context = f"""
            Expéditeur: {sender}
            Sujet: {subject}
            Contenu: {mail_content}
            """
            
            functions = [{
                "name": "classify_email",
                "description": "Classifie un email selon différentes catégories",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "primary_category": {
                            "type": "string",
                            "enum": categories,
                            "description": "Catégorie principale de l'email"
                        },
                        "secondary_categories": {
                            "type": "array",
                            "items": {"type": "string", "enum": categories},
                            "description": "Catégories secondaires applicables"
                        },
                        "confidence_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Score de confiance de la classification"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Justification de la classification"
                        },
                        "requires_human_review": {
                            "type": "boolean",
                            "description": "Indique si une révision humaine est recommandée"
                        }
                    },
                    "required": ["primary_category", "confidence_score", "reasoning"]
                }
            }]
            
            system_prompt = f"""
            Tu es un système de classification d'emails expert. 
            Tu DOIS utiliser la fonction classify_email pour analyser et classer les emails.
            Ne réponds jamais directement sans utiliser cette fonction.
            
            Tu dois analyser le contenu, l'expéditeur et le sujet des emails pour les classer 
            dans les catégories suivantes: {', '.join(categories)}.
            
            Fournis toujours une justification claire de tes classifications.
            """
            
            user_prompt = f"""
            Utilise la fonction classify_email pour classifier cet email selon les catégories disponibles:
            
            {mail_context}
            
            Catégories disponibles: {', '.join(categories)}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.api_client.make_request(messages, functions)
            
            return self._process_response(response, 'classification', categories, sender, subject)
            
        except Exception as e:
            logger.error(f"Error classifying mail: {e}")
            return {
                'success': False,
                'error': str(e),
                'classification': {
                    'primary_category': 'normal',
                    'confidence_score': 0.0,
                    'reasoning': f'Erreur lors de la classification: {str(e)}'
                }
            }
    
    def _process_response(self, response: Dict[str, Any], operation_type: str, *args) -> Dict[str, Any]:
        """
        Process Albert API response and extract function call results or content.
        
        Args:
            response: Raw response from Albert API
            operation_type: Type of operation ('summary', 'answer', 'classification')
            *args: Additional arguments specific to the operation
            
        Returns:
            Processed response dictionary
        """
        try:
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            # Check for new tool_calls format first
            if 'tool_calls' in message and message['tool_calls']:
                tool_call = message['tool_calls'][0]
                if tool_call['type'] == 'function':
                    function_call = tool_call['function']
                    function_data = json.loads(function_call['arguments'])
                    logger.info(f"Successfully processed {operation_type} using function call")
                    return self._format_success_response(operation_type, function_data, *args)
            
            # Check for legacy function_call format
            elif 'function_call' in message:
                function_call = message['function_call']
                function_data = json.loads(function_call['arguments'])
                logger.info(f"Successfully processed {operation_type} using function call")
                return self._format_success_response(operation_type, function_data, *args)
            
            # Albert API uses content-based responses
            content = message.get('content', '')
            if content:
                content = content.strip()
                logger.info(f"Successfully processed {operation_type} using content response")
                parsed_data = self._parse_content_response(operation_type, content, *args)
                return self._format_success_response(operation_type, parsed_data, *args)
            
            # No content at all
            logger.error(f"No content received from Albert API for {operation_type}")
            return self._format_error_response(operation_type, 'Aucune réponse reçue de l\'API Albert')
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse function arguments for {operation_type}: {e}")
            return self._format_error_response(operation_type, f'Erreur de parsing JSON: {str(e)}')
        except Exception as e:
            logger.error(f"Error processing response for {operation_type}: {e}")
            return self._format_error_response(operation_type, str(e))
    
    def _parse_content_response(self, operation_type: str, content: str, *args) -> Dict[str, Any]:
        """Parse content response based on operation type."""
        if operation_type == 'summary':
            return self.parser.parse_summary_content(content)
        elif operation_type == 'answer':
            tone = args[1] if len(args) > 1 else 'professional'
            return self.parser.parse_answer_content(content, tone)
        elif operation_type == 'classification':
            categories = args[0] if args else []
            return self.parser.parse_classification_content(content, categories)
        else:
            return {'content': content}
    
    def _format_success_response(self, operation_type: str, data: Dict[str, Any], *args) -> Dict[str, Any]:
        """Format successful response based on operation type."""
        base_response = {'success': True}
        
        if operation_type == 'summary':
            sender, subject = args if len(args) >= 2 else ('', '')
            base_response.update({
                'summary': data,
                'original_sender': sender,
                'original_subject': subject
            })
        elif operation_type == 'answer':
            context, tone = args if len(args) >= 2 else ('', 'professional')
            base_response.update({
                'response': data,
                'context_used': context,
                'tone_requested': tone
            })
        elif operation_type == 'classification':
            categories = args[0] if args else []
            sender = args[1] if len(args) > 1 else ''
            subject = args[2] if len(args) > 2 else ''
            base_response.update({
                'classification': data,
                'available_categories': categories,
                'original_sender': sender,
                'original_subject': subject
            })
        
        return base_response
    
    def _format_error_response(self, operation_type: str, error_message: str) -> Dict[str, Any]:
        """Format error response based on operation type."""
        base_response = {'success': False, 'error': error_message}
        
        if operation_type == 'summary':
            base_response['summary'] = {'summary': 'Erreur lors du résumé de l\'email.'}
        elif operation_type == 'answer':
            base_response['response'] = {'response': 'Erreur lors de la génération de la réponse.'}
        elif operation_type == 'classification':
            base_response['classification'] = {
                'primary_category': 'normal',
                'confidence_score': 0.0,
                'reasoning': 'Erreur - aucune réponse de l\'API.'
            }
        
        return base_response
